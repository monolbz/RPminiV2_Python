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

### 6. Create Input File

Copy the example input file and add your addresses:

```bash
cp input.txt.example input.txt
```

**Windows:**
```bash
copy input.txt.example input.txt
```

Edit `input.txt` with your addresses (one per line):
- First line: Starting point
- Following lines: Destinations to visit
- Minimum: 2 addresses
- Maximum: 26 addresses (1 origin + 25 waypoints)
- No duplicate addresses allowed

## Usage

### Basic Usage (Using input.txt)

Run with addresses from `input.txt`:

```bash
python run_optimizer.py
```

### Custom Addresses (Command Line)

Provide your own addresses as command-line arguments (overrides `input.txt`):

```bash
python run_optimizer.py "Address 1" "Address 2" "Address 3" "Address 4"
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

You can adjust these constants:

- `FUEL_CONSUMPTION_L_PER_100KM` in `route_optimizer/utils.py`: Fuel consumption rate (default: 8.5 L/100km)
- `FUEL_PRICE_EUR_PER_L` in `route_optimizer/utils.py`: Fuel price (default: €1.50/L)
- `CACHE_EXPIRY_DAYS` in `route_optimizer/cache.py`: Cache validity period (default: 30 days)

## Project Structure

```
RPminiV2_Python/
├── route_optimizer/          # Main package (modular structure)
│   ├── __init__.py          # Package initialization
│   ├── main.py              # Main application logic and display
│   ├── api.py               # Google Maps API integration
│   ├── cache.py             # Cache management
│   ├── utils.py             # Utility functions (calculations, formatting, URLs)
│   └── input_handler.py     # Input file reading and validation
├── run_optimizer.py         # Entry point script
├── requirements.txt         # Python dependencies
├── input.txt.example        # Example input file (committed)
├── input.txt               # Your addresses (gitignored, create from example)
├── .env                    # API keys (gitignored)
├── .cache/                 # API response cache (gitignored, auto-created)
└── README.md               # This file
```

### Modular Architecture Benefits

The new modular structure (v2.0.0) provides:
- **Separation of Concerns**: Each module handles a specific responsibility
- **Better Testability**: Individual components can be tested in isolation
- **Easier Maintenance**: Changes are localized to specific modules
- **Code Reusability**: Modules can be imported and used independently
- **Team Collaboration**: Multiple developers can work on different modules

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
