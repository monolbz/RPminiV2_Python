# Madrid Route Optimizer

A Python tool that optimizes delivery routes in Madrid using the Google Maps API, with automatic fuel cost estimation and intelligent caching.

## Features

- **Route Optimization**: Uses Google Maps waypoint optimization to find the most efficient delivery route
- **Fuel Cost Estimation**: Automatically calculates fuel consumption and costs based on route distance
- **Smart Caching**: Caches Google Maps API responses for 30 days to minimize API calls and costs
- **Comparison Analytics**: Shows side-by-side comparison of original vs. optimized routes
- **Multiple Addresses**: Support for multiple waypoints with automatic optimization

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/monolbz/RPminiV2_Python.git
cd RPminiV2_Python
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Google Maps API Key

Create a `.env` file in the project root:

```env
GOOGLE_MAPS_API_KEY=your_api_key_here
```

Get your API key from: https://console.cloud.google.com/google/maps-apis

## Usage

### Basic Usage

Run with the default Madrid addresses:

```bash
python route_optimizer.py
```

### Custom Addresses

Provide your own addresses as command-line arguments:

```bash
python route_optimizer.py "Address 1" "Address 2" "Address 3" "Address 4"
```

### Example Output

```
==============================================================
Madrid Route Optimizer
==============================================================

Input addresses:
  1. Calle de Hortaleza 63, 28004 Madrid, Spain
  2. Calle del Barquillo 15, 28004 Madrid, Spain
  3. Calle de Velázquez 72, 28001 Madrid, Spain
  ...

==============================================================
ORIGINAL ROUTE (Input Order)
==============================================================
  1. Calle de Hortaleza 63, 28004 Madrid, Spain
  ...

Total Distance:      25.40 km
Total Time:          01:15
Fuel Consumption:    2.16 L
Estimated Fuel Cost: €3.24

==============================================================
OPTIMIZED ROUTE (Google Maps Optimized)
==============================================================
  1. Calle de Hortaleza 63, 28004 Madrid, Spain
  ...

Total Distance:      18.60 km
Total Time:          00:52
Fuel Consumption:    1.58 L
Estimated Fuel Cost: €2.37

==============================================================
SAVINGS
==============================================================
Distance Saved:      6.80 km (26.8%)
Time Saved:          00:23 (saved)
Fuel Cost Saved:     €0.87 (26.8%)
==============================================================
```

## Configuration

You can adjust these constants in `route_optimizer.py`:

- `FUEL_CONSUMPTION_L_PER_100KM`: Fuel consumption rate (default: 8.5 L/100km)
- `FUEL_PRICE_EUR_PER_L`: Fuel price (default: €1.50/L)
- `CACHE_EXPIRY_DAYS`: Cache validity period (default: 30 days)

## Project Structure

```
RPminiV2_Python/
├── route_optimizer.py    # Main script
├── requirements.txt      # Python dependencies
├── .env                  # API keys (not committed)
├── .cache/              # API response cache (auto-created)
└── README.md            # This file
```

## Dependencies

- `python-dotenv==1.0.0` - Environment variable management
- `requests==2.31.0` - HTTP requests for Google Maps API

## How It Works

1. **Input**: Takes a starting point and multiple destination addresses
2. **API Calls**: Makes two Google Maps API requests:
   - One with original address order
   - One with Google's optimized waypoint order
3. **Caching**: Stores API responses locally to reduce costs
4. **Analysis**: Calculates distance, time, and fuel costs for both routes
5. **Output**: Displays detailed comparison and savings

## Development Setup

This project uses a virtual environment to isolate dependencies:

1. Virtual environment created at `./venv`
2. All dependencies managed via `requirements.txt`
3. VSCode configured to use `.\venv\Scripts\python.exe`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Created by [@monolbz](https://github.com/monolbz)

## Contributing

Feel free to open issues or submit pull requests for improvements!
