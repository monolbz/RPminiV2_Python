#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feedback Manager — WhatsApp NPS survey system.

Surveys are triggered immediately after the user's 3rd successful route
optimization (all tiers). Q1 is sent as a follow-up message in the same
conversation window, so no 24h-window issues arise.

Survey flow (3 questions, all in Spanish):
  Q1: NPS score 1–10
  Q2: Open free-text feedback
  Q3: Discovery source (numbered 1–6)

User can type 'saltar' at any step to exit gracefully.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
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
    "¡Hola! Acabas de completar tu 3ª ruta con *Mi Ruta Pro* 🎉\n"
    "Nos encantaría saber qué te parece. Son solo 3 preguntas rápidas.\n\n"
    "*Pregunta 1:* Del 1 al 10, ¿qué nota le darías a Mi Ruta Pro?\n\n"
    "_Responde con un número del 1 al 10, o escribe *saltar* para omitir la encuesta._"
)

MSG_Q2 = (
    "¡Gracias por tu nota!\n\n"
    "*Pregunta 2:* ¿Qué es lo que más te ha gustado, o qué cambiarías?\n\n"
    "_Escribe lo que quieras (o *saltar* para omitir)._"
)

MSG_Q3 = (
    "*Pregunta 3:* ¿Cómo conociste Mi Ruta Pro? Responde con el número:\n\n"
    "1 — Me lo recomendó alguien\n"
    "2 — Búsqueda en Google / web\n"
    "3 — Instagram\n"
    "4 — Grupo de WhatsApp o Facebook\n"
    "5 — YouTube\n"
    "6 — Cartel, flyer o anuncio\n\n"
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

_DISCOVERY_MAP = {
    '1': 'referral',
    '2': 'google',
    '3': 'instagram',
    '4': 'whatsapp_groups',
    '5': 'youtube',
    '6': 'flyer',
}


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
    # Route-triggered survey
    # ------------------------------------------------------------------

    def trigger_survey_after_route(self, identifier: str, phone_number_id: str) -> bool:
        """
        Called right after the user's 3rd successful route optimization.
        Creates a survey record and immediately sends Q1 as a follow-up message.
        Returns True if the survey was sent, False otherwise.
        """
        if not self.db:
            return False
        try:
            with self.db.get_session() as session:
                user = User.find_by_identifier(session, identifier)
                if not user:
                    return False
                if user.routes_used_lifetime != 3:
                    return False
                existing = session.query(FeedbackSurvey).filter(
                    FeedbackSurvey.user_id == user.user_id
                ).first()
                if existing:
                    return False
                survey = FeedbackSurvey(
                    user_id=user.user_id,
                    phone_number=user.phone_number,
                    status='sent',
                    current_step='q1',
                    sent_at=datetime.now(timezone.utc),
                )
                session.add(survey)
                session.commit()

            from .message_sender import MessageSender
            response = {
                'to_number': identifier,
                'phone_number_id': phone_number_id,
                'message_text': MSG_Q1,
                'timestamp': datetime.now().isoformat(),
            }
            MessageSender().send_reply(response)
            logger.info(f"Survey Q1 sent after 3rd route for {identifier}")
            return True
        except Exception as e:
            logger.error(f"trigger_survey_after_route({identifier}) error: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Inbound message handling
    # ------------------------------------------------------------------

    def get_active_survey(self, phone_number: str) -> Optional[dict]:
        """
        Return the active survey data for a user, or None.
        A survey is 'active' if status is in ('sent', 'in_progress').
        Called by message_processor to decide whether to intercept.
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
        """
        if not self.db:
            return None
        try:
            with self.db.get_session() as session:
                survey = self._get_active_survey_obj(session, phone_number)
                if not survey:
                    return None

                text = message_text.strip()

                # Global skip
                if text.lower() == 'saltar':
                    survey.status = 'skipped'
                    survey.skipped_at = datetime.now(timezone.utc)
                    session.commit()
                    logger.info(f"Survey skipped by {phone_number} at step {survey.current_step}")
                    return MSG_SKIPPED

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
        discovery = self._parse_q3(text)
        # Store discovery source in price_suggestion (no CHECK constraint).
        # willing_to_pay stays NULL — its CHECK constraint (si/no/quizas) cannot hold
        # discovery source values and a migration is not needed here.
        survey.price_suggestion = discovery
        survey.current_step = 'done'
        survey.status = 'completed'
        survey.completed_at = datetime.now(timezone.utc)
        session.commit()
        logger.info(
            f"Survey completed for {survey.phone_number or survey.user_id}: "
            f"nps={survey.nps_score}, discovery={discovery}"
        )
        return MSG_CLOSING

    def _parse_q3(self, text: str) -> str:
        """
        Parse Q3 discovery-source response. Returns a short string key.
        Accepts digits 1–6 or keyword fallbacks. Unknown → 'other'.
        """
        t = text.strip()
        if t in _DISCOVERY_MAP:
            return _DISCOVERY_MAP[t]
        # Keyword fallback for partial matches
        tl = t.lower()
        if 'google' in tl or 'web' in tl or 'busq' in tl:
            return 'google'
        if 'instagram' in tl or 'insta' in tl:
            return 'instagram'
        if 'whatsapp' in tl or 'facebook' in tl or 'grupo' in tl:
            return 'whatsapp_groups'
        if 'youtube' in tl or 'video' in tl:
            return 'youtube'
        if 'cartel' in tl or 'flyer' in tl or 'anuncio' in tl:
            return 'flyer'
        if 'recom' in tl or 'amigo' in tl or 'conocido' in tl:
            return 'referral'
        return f'other:{t[:80]}' if t else 'other'

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_active_survey_obj(self, session, phone_number: str) -> Optional[FeedbackSurvey]:
        """Return the active FeedbackSurvey ORM object, or None."""
        user = User.find_by_identifier(session, phone_number)
        if not user:
            return None
        return (
            session.query(FeedbackSurvey)
            .filter(
                FeedbackSurvey.user_id == user.user_id,
                FeedbackSurvey.status.notin_(['completed', 'skipped']),
            )
            .first()
        )


# Module-level singleton
feedback_manager = FeedbackManager()
