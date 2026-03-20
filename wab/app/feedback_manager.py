#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feedback Manager — WhatsApp NPS survey system.

Surveys are triggered on day 3 of use (users with created_at <= now()-3d
and routes_used_lifetime >= 1 who have not yet received a survey).

Survey flow (3 questions, all in Spanish):
  Q1: NPS score 1–10
  Q2: Open free-text feedback
  Q3: Willingness to pay (si [precio] / no / quizas)

User can type 'saltar' at any step to exit gracefully.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db_manager import get_db_manager
from database.models import User, FeedbackSurvey
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Spanish message constants
# ---------------------------------------------------------------------------

MSG_Q1 = (
    "¡Hola! Llevas unos días usando *Mi Ruta Pro* y nos encantaría saber tu opinión.\n"
    "Son solo 3 preguntas rápidas.\n\n"
    "*Pregunta 1:* Del 1 al 10, ¿qué nota le darías a Mi Ruta Pro?\n\n"
    "_Responde con un número del 1 al 10, o escribe *saltar* para omitir la encuesta._"
)

MSG_Q2 = (
    "¡Gracias por tu nota!\n\n"
    "*Pregunta 2:* ¿Qué es lo que más te ha gustado, o qué cambiarías?\n\n"
    "_Escribe lo que quieras (o *saltar* para omitir)._"
)

MSG_Q3 = (
    "*Pregunta 3:* ¿Cuánto pagarías por Mi Ruta Pro? "
    "Puedes indicar precio por uso o mensual.\n\n"
    "Ejemplos: _3€ por ruta_, _50€ por mes_, _no_, _quizas_\n\n"
    "_O escribe *saltar* para terminar aquí._"
)

MSG_CLOSING = (
    "¡Muchas gracias por tu tiempo y opinión! Tu feedback nos ayuda a mejorar.\n\n"
    "Si conoces a alguien que haga entregas o gestione rutas, cuéntale que existe "
    "*Mi Ruta Pro*. ¡Les ahorraremos tiempo y dinero! Hasta pronto!"
)

MSG_SKIPPED = (
    "Sin problema. Si en otro momento quieres darnos tu opinión, estamos aquí. ¡Hasta pronto!"
)

MSG_INVALID_NPS = (
    "Por favor, responde con un número del *1 al 10*.\n"
    "_O escribe *saltar* para omitir la encuesta._"
)


class FeedbackManager:
    """Manages the NPS feedback survey lifecycle."""

    def __init__(self):
        try:
            self.db = get_db_manager()
            logger.info("FeedbackManager initialized")
        except Exception as e:
            logger.error(f"FeedbackManager: DB init failed: {e}")
            self.db = None

    # ------------------------------------------------------------------
    # Cron helpers
    # ------------------------------------------------------------------

    def find_eligible_users(self) -> list[str]:
        """
        Return phone numbers of users eligible for a survey:
          - Account created >= 3 days ago
          - At least 1 route used in their lifetime
          - No existing non-completed/skipped survey
          - User not soft-deleted
        """
        if not self.db:
            return []
        try:
            with self.db.get_session() as session:
                cutoff = datetime.now(timezone.utc) - timedelta(days=3)

                # Users who have ever had a survey (any status) — one survey per user, ever
                active_survey_phones = (
                    session.query(FeedbackSurvey.phone_number)
                    .subquery()
                )

                eligible = (
                    session.query(User.phone_number)
                    .filter(
                        User.created_at <= cutoff,
                        User.routes_used_lifetime >= 1,
                        User.deleted_at.is_(None),
                        User.phone_number.notin_(active_survey_phones),
                    )
                    .all()
                )
                phones = [row.phone_number for row in eligible]
                logger.info(f"Feedback cron: {len(phones)} eligible users")
                return phones
        except Exception as e:
            logger.error(f"find_eligible_users error: {e}", exc_info=True)
            return []

    def create_pending_survey(self, phone_number: str) -> bool:
        """Insert a new survey row with status='pending'. Returns True on success."""
        if not self.db:
            return False
        try:
            with self.db.get_session() as session:
                survey = FeedbackSurvey(
                    phone_number=phone_number,
                    status='pending',
                    current_step='q1',
                )
                session.add(survey)
                session.commit()
                logger.info(f"Created pending survey for {phone_number}")
                return True
        except Exception as e:
            logger.error(f"create_pending_survey({phone_number}) error: {e}", exc_info=True)
            return False

    def send_q1(self, phone_number: str, sender) -> bool:
        """
        Attempt to deliver Q1 to the user.

        For Twilio — send immediately (no 24h window restriction).
        For Meta — only send if user is within a 24h conversation window;
                   otherwise leave status='pending' for next inbound intercept.

        Args:
            phone_number: E.164 phone number
            sender: MessageSender instance (or None to skip actual send)

        Returns:
            True if Q1 was sent, False if left as pending.
        """
        from ..config.config import Config
        config = Config()

        should_send = True

        if config.MESSAGING_PROVIDER == 'meta':
            # Check conversation window
            try:
                from ..utils.conversation_tracker_db import ConversationTracker
                tracker = ConversationTracker()
                in_window = tracker.is_within_window(phone_number)
                if not in_window:
                    logger.info(
                        f"Meta: {phone_number} outside 24h window — survey left as pending"
                    )
                    should_send = False
            except Exception as e:
                logger.warning(f"Could not check conversation window for {phone_number}: {e}")
                should_send = False

        if should_send and sender:
            try:
                from .message_sender import MessageSender
                # Build a minimal response dict that MessageSender understands
                response = {
                    'to_number': phone_number,
                    'phone_number_id': config.WHATSAPP_PHONE_NUMBER_ID,
                    'message_text': MSG_Q1,
                    'timestamp': datetime.now().isoformat(),
                }
                sender.send_reply(response)
                self._mark_sent(phone_number)
                logger.info(f"Q1 sent to {phone_number}")
                return True
            except Exception as e:
                logger.error(f"send_q1({phone_number}) send error: {e}", exc_info=True)
                return False

        return False

    def _mark_sent(self, phone_number: str) -> None:
        """Update survey status to 'sent' after Q1 is delivered."""
        if not self.db:
            return
        try:
            with self.db.get_session() as session:
                survey = self._get_active_survey_obj(session, phone_number)
                if survey:
                    survey.status = 'sent'
                    survey.sent_at = datetime.now(timezone.utc)
                    session.commit()
        except Exception as e:
            logger.error(f"_mark_sent({phone_number}) error: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Inbound message handling
    # ------------------------------------------------------------------

    def get_active_survey(self, phone_number: str) -> Optional[dict]:
        """
        Return the active survey data for a user, or None.

        A survey is 'active' if status is in ('pending','sent','in_progress').
        This is called by message_processor to decide whether to intercept.
        """
        if not self.db:
            return None
        try:
            with self.db.get_session() as session:
                survey = self._get_active_survey_obj(session, phone_number)
                if not survey:
                    return None
                return {
                    'survey_id': str(survey.survey_id),
                    'status': survey.status,
                    'current_step': survey.current_step,
                }
        except Exception as e:
            logger.error(f"get_active_survey({phone_number}) error: {e}", exc_info=True)
            return None

    def handle_incoming(self, phone_number: str, message_text: str, phone_number_id: str) -> Optional[str]:
        """
        Process an inbound message during an active survey.

        Returns the reply string to send, or None if no survey is active.

        Intercept priority:
        1. If status='pending' → this is the user's first message since cron — deliver Q1 now.
        2. If status='sent' or 'in_progress' → route to current step handler.
        """
        if not self.db:
            return None
        try:
            with self.db.get_session() as session:
                survey = self._get_active_survey_obj(session, phone_number)
                if not survey:
                    return None

                text = message_text.strip()

                # Pending → deliver Q1 now (Meta outside-window case)
                if survey.status == 'pending':
                    survey.status = 'sent'
                    survey.sent_at = datetime.now(timezone.utc)
                    session.commit()
                    logger.info(f"Pending survey activated on inbound message for {phone_number}")
                    return MSG_Q1

                # Active survey — check for global skip
                if text.lower() == 'saltar':
                    survey.status = 'skipped'
                    survey.skipped_at = datetime.now(timezone.utc)
                    session.commit()
                    logger.info(f"Survey skipped by {phone_number} at step {survey.current_step}")
                    return MSG_SKIPPED

                # Route to current step
                step = survey.current_step

                if step == 'q1':
                    return self._handle_q1(session, survey, text)
                elif step == 'q2':
                    return self._handle_q2(session, survey, text)
                elif step == 'q3':
                    return self._handle_q3(session, survey, text)

                return None

        except Exception as e:
            logger.error(f"handle_incoming({phone_number}) error: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Step handlers
    # ------------------------------------------------------------------

    def _handle_q1(self, session, survey: FeedbackSurvey, text: str) -> str:
        try:
            score = int(text.strip())
            if 1 <= score <= 10:
                survey.nps_score = score
                survey.current_step = 'q2'
                survey.status = 'in_progress'
                session.commit()
                return MSG_Q2
        except ValueError:
            pass
        return MSG_INVALID_NPS

    def _handle_q2(self, session, survey: FeedbackSurvey, text: str) -> str:
        survey.free_text = text
        survey.current_step = 'q3'
        session.commit()
        return MSG_Q3

    def _handle_q3(self, session, survey: FeedbackSurvey, text: str) -> str:
        willing, price = self._parse_q3(text)
        survey.willing_to_pay = willing
        if price:
            survey.price_suggestion = price
        survey.current_step = 'done'
        survey.status = 'completed'
        survey.completed_at = datetime.now(timezone.utc)
        session.commit()
        logger.info(
            f"Survey completed for {survey.phone_number}: "
            f"nps={survey.nps_score}, willing={willing}"
        )
        return MSG_CLOSING

    def _parse_q3(self, text: str) -> tuple[str, Optional[str]]:
        """
        Parse Q3 response. Returns (willing_to_pay, price_suggestion).

        Accepted formats:
          'no'             → ('no', None)
          'quizas'         → ('quizas', None)
          'si'             → ('si', None)
          'si 5€/mes'      → ('si', '5€/mes')
          'si 0.50€'       → ('si', '0.50€')
        """
        t = text.strip().lower()

        if t == 'no' or t.startswith('no '):
            return 'no', None

        if t in ('quizas', 'quizás', 'quiza', 'quizá', 'tal vez', 'talvez'):
            return 'quizas', None

        if t == 'si' or t in ('sí',):
            return 'si', None

        if t.startswith('si ') or t.startswith('sí '):
            price = text.strip()[3:].strip()  # preserve original casing for price
            return 'si', price[:100] if price else None

        # Fallback: store raw as quizas with price_suggestion holding the raw text
        return 'quizas', text[:100]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_active_survey_obj(self, session, phone_number: str) -> Optional[FeedbackSurvey]:
        """Return the active FeedbackSurvey ORM object, or None."""
        return (
            session.query(FeedbackSurvey)
            .filter(
                FeedbackSurvey.phone_number == phone_number,
                FeedbackSurvey.status.notin_(['completed', 'skipped']),
            )
            .first()
        )


# Module-level singleton
feedback_manager = FeedbackManager()
