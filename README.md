# OpenFlight

A modern FastAPI-based web application for flight management and booking services.

## Features

- 🚀 Fast and modern API built with FastAPI
- 📝 Automatic API documentation with Swagger UI
- 🔒 Type safety with Pydantic models
- 🧪 Comprehensive testing with pytest
- 🐳 Docker support for easy deployment
- 📦 Modern Python packaging with pyproject.toml

## Requirements

- Python 3.8+
- FastAPI
- Uvicorn

## Installation

### Using pip

1. Clone the repository:
```bash
git clone https://github.com/yourusername/openflight.git
cd openflight
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Using pip with pyproject.toml

```bash
pip install -e .
```

For development dependencies:
```bash
pip install -e ".[dev]"
```

## Usage

### Running the Application

Start the development server:
```bash
uvicorn main:app --reload
```

The API will be available at:
- Main application: http://127.0.0.1:8000
- Interactive API docs (Swagger UI): http://127.0.0.1:8000/docs
- Alternative API docs (ReDoc): http://127.0.0.1:8000/redoc

### API Endpoints

- `GET /` - Welcome message
- `GET /hello/{name}` - Personalized greeting

## Development

### Code Formatting

Format code with Black:
```bash
black .
```

Sort imports with isort:
```bash
isort .
```

### Linting and Type Checking

Use Ruff for linting:
```bash
ruff check .
```

Optionally auto-fix issues:
```bash
ruff check . --fix
```

Run MyPy for static type checking:
```bash
mypy .
```

### Testing

Run tests with pytest:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=openflight
```

### Docker

Build the Docker image:
```bash
docker build -t openflight .
```

Run the container:
```bash
docker run -p 8000:8000 openflight
```

Or use docker-compose:
```bash
docker-compose up
```

## Project Structure

```
openflight/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application factory (app/create_app)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # APIRouter with endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Settings (env-based)
│   │   └── logging.py       # Logging setup
│   └── models/
│       ├── __init__.py
│       └── common.py        # Pydantic response models
├── main.py                   # Thin wrapper re-exporting app from app.main
├── scripts/
│   ├── download_data.py
│   └── combine_data.py
├── impoted_data/             # Local datasets (git-ignored)
├── tests/                    # Test files
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Modern Python project configuration
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker Compose configuration
├── .gitignore                # Git ignore patterns
└── README.md                 # Project documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure they pass
5. Format your code (`black .` and `isort .`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contributing guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you have any questions or need help, please:
- Check the [documentation](https://github.com/yourusername/openflight/wiki)
- Open an [issue](https://github.com/yourusername/openflight/issues)
- Join our [discussions](https://github.com/yourusername/openflight/discussions)

## Roadmap

- [ ] User authentication and authorization
- [ ] Flight search and booking functionality
- [ ] Payment integration
- [ ] Email notifications
- [ ] Admin dashboard
- [ ] Mobile API endpoints
- [ ] Real-time flight updates

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - The web framework used
- [Uvicorn](https://www.uvicorn.org/) - ASGI server implementation
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation library

## Dataset Download

A helper script is provided to download public aviation datasets into the local impoted_data directory (ignored by Git).

Files downloaded:
- airports.csv
- runways.csv
- airport-comments.csv
- airport-frequencies.csv
- regions.csv
- navaids.csv
- countries.csv
- airlines.dat
- routes.dat

Usage:

1. Ensure dependencies are installed (once per environment):
```bash
pip install -r requirements.txt
```

2. Run the downloader (default output: impoted_data):
```bash
python scripts/download_data.py
```

Options:
- Choose a different output directory:
```bash
python scripts/download_data.py -o data
```
- Force re-download and overwrite existing files:
```bash
python scripts/download_data.py -f
```

The downloaded files will be saved under the chosen directory, e.g. impoted_data/airports.csv.


## Data: Combine OurAirports CSVs to JSON

This project includes a small utility to combine multiple OurAirports CSV files into a single JSON list of airport objects enriched with country, region, and comments.

Inputs expected in impoted_data/:
- airports.csv
- countries.csv
- regions.csv
- airport-comments.csv

The files can be downloaded/updated with:

```bash
python scripts/download_data.py --output impoted_data
```

Generate the combined JSON:

```bash
python scripts/combine_data.py \
  --input-dir impoted_data \
  --output impoted_data/airports_combined.json \
  --indent 2
```

Quick preview to stdout (first 5 airports, minified):

```bash
python scripts/combine_data.py --input-dir impoted_data --limit 5 --indent 0
```

Notes:
- Joins use airports.iso_country -> countries.code, airports.iso_region -> regions.code.
- Comments are attached by airportRef (airport id), falling back to airportIdent (airport ident) when needed.
- Numeric fields such as id and elevation_ft are parsed to integers when possible; missing values are set to null.
- The output is a JSON array where each airport includes nested objects: country, region, and a comments list.


## Configuration

The application reads a few environment variables:

- ALLOWED_ORIGINS: Comma-separated list of origins for CORS. Use * to allow all (default).
- ENVIRONMENT: Arbitrary environment label (e.g., development, production). Default: production.
- APP_NAME: Application title shown in docs. Default: OpenFlight API.

Examples:

```bash
ALLOWED_ORIGINS="https://example.com, http://localhost:3000" \
APP_NAME="OpenFlight API" \
uvicorn main:app --host 0.0.0.0 --port 8000
```
