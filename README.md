# Vendor Intelligence Collector

A sophisticated data collection system designed to gather and analyze vendor information across various industries and locations.

## Features

- **Multi-Industry Support**: Currently supports data collection for:
  - Chiropractic Services
  - Optometry Services
  - Auto Repair Services

- **Location-Based Processing**:
  - Filter by State
  - Filter by City
  - Batch processing of locations
  - Progress tracking and resumable operations

- **Modern Web Interface**:
  - Real-time progress monitoring
  - Interactive location filters
  - Batch processing controls
  - Visual progress indicators
  - Error handling and reporting

- **Advanced Processing Capabilities**:
  - Parallel processing for improved performance
  - Automatic query generation using AI
  - Smart vendor site summarization
  - Robust error handling and recovery

## Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Google Chrome (for web scraping)
- Valid API keys for:
  - SERP API
  - Google Search API

### Installation

1. Clone the repository:
```bash
git clone https://github.com/thinksmartgroup/Vendor-Intel.git
cd Vendor-Intel
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the root directory with the following:
```
SERPAPI_KEY=your_google_api_key
GEMINI_API_KEY=your_gemini_api_key
```

## Usage

### Starting the Application

1. Run the web interface:
```bash
python web_interface.py
```
The server will start at `http://localhost:5001`

2. Access the web interface in your browser at `http://localhost:5001`

### Processing Data

1. Select an industry from the dropdown menu
2. (Optional) Filter locations by:
   - State
   - City
3. Click "Process Next Batch" to start processing
4. Monitor progress in real-time through the interface
5. Use the "Stop Processing" button if needed

### Results

- Results are automatically saved in JSON format
- Files are named with timestamp and industry:
  - `results_[industry]_[timestamp].json`
  - `errors_[industry]_[timestamp].json`

## Project Structure

- `web_interface.py`: Main web application and API endpoints
- `location_manager.py`: Handles location data and batch processing
- `parallel_processor.py`: Manages concurrent processing tasks
- `query_generator.py`: Generates search queries using Gemini AI
- `search_runner.py`: Executes web searches
- `summarizer.py`: Processes and summarizes vendor information
- `templates/`: Contains web interface HTML templates
- `static/`: Static assets for the web interface

## Error Handling

- Failed operations are logged and saved
- Processing can be stopped and resumed
- Automatic retry mechanism for failed requests
- Detailed error reporting in the web interface

## Performance

- Processes locations in batches of 100
- Parallel processing with configurable worker count
- Efficient data storage and retrieval
- Real-time progress updates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

Proprietary - ThinkSmart Group

## Support

For support, please contact the development team at ThinkSmart Group. 
