# News Condenser Service

A Python service for processing and condensing news content using AI summarization.

---

**Upstream Integration: NewsCrawler API**

This service is designed to work with the [NewsCrawler API](https://github.com/your-org/newscrawler) as its upstream data source. The News Condenser fetches news articles from the NewsCrawler API (expected to be running at `http://localhost:8000/news`), then uses AI to generate a comprehensive summary of the results. You must have the NewsCrawler API running and accessible for this service to function correctly.

---

## Architecture Overview

```
User → News Condenser Service → NewsCrawler API → News Sources
```

- **NewsCrawler API**: Aggregates and extracts news articles from various sources, exposing them via a REST API.
- **News Condenser Service**: Accepts user queries, fetches articles from the NewsCrawler API, and uses DeepSeek AI to generate a 1000-word summary of all events related to the search field.
- **Frontend**: Simple web form for user interaction.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows:
```bash
.\venv\Scripts\activate
```
- Unix/MacOS:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with:
```
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

You can get a DeepSeek API key from: https://platform.deepseek.com/

## Running the Service

To run the service:
```bash
python src/main.py
```

Make sure the NewsCrawler API is running and accessible at `http://localhost:8000/news` before starting this service.

## Features

- **NewsCrawler API Integration**: Fetches news articles from the NewsCrawler API as the upstream source
- **AI Summarization**: Uses DeepSeek API to generate 1000-word summaries
- **Form Interface**: Web-based form for easy interaction
- **Multiple Sources**: Support for The News API, Guardian, NY Times, and GNews (via NewsCrawler)
- **Flexible Filtering**: Filter by categories, domains, dates, and search terms

## Project Structure

```
newsCondenser/
├── src/
│   ├── main.py         # Main service entry point
│   ├── config.py       # Configuration settings
│   └── services/       # Service implementations
├── static/
│   └── index.html      # Frontend HTML page
├── tests/              # Test files
├── requirements.txt    # Project dependencies
├── .env.example       # Environment variables template
└── README.md          # This file
``` 