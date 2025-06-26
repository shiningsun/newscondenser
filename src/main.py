from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import requests
import openai
import os
from dotenv import load_dotenv
from typing import Dict, Optional, List

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="News Condenser Service")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

async def summarize_with_deepseek(article_content: List[Dict], search_query: str, word_length: int = 1000, persona: str = "", topic: str = "", perspective: str = "") -> str:
    """Analyze using DeepSeek API."""
    try:
        # Check if API key is available
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key or api_key == "your_deepseek_api_key_here":
            return "Error: DeepSeek API key not configured. Please set DEEPSEEK_API_KEY in your .env file."
        
        # Initialize OpenAI client with DeepSeek API
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        # Prepare context from articles
        context = ""
        for i, article in enumerate(article_content, 1):
            context += f"Article {i}:\n"
            context += f"Title: {article.get('title', '')}\n"
            context += f"Content: {article.get('content', '')}\n\n"
        
        # Create the prompt for analysis
        prompt = f"""As a {persona} and based on the news articles provided below, which are the search results for '{search_query}', please write your analysis of the topic '{topic}' in around {word_length}-word long.

Search Query: \"{search_query}\"
Topic to Analyze: \"{topic}\"
Persona: \"{persona}\"
Perspective: \"{perspective}\"

Articles:
{context}

Please structure your analysis to:
1.  Create quick overview related to \"{topic}\" that synthesize key information, facts, and figures from the articles.
2.  Provide context and background where necessary to explain the significance of the events.
3.  Present 2-4 strategic options for how the {perspective} should proceed regarding \"{topic}\".
4.  For each option, provide detailed pros and cons from a {perspective} perspective.
5.  Maintain an objective tone throughout the analysis.
6.  Be approximately {word_length} words long.

Detailed Analysis of \"{topic}\" from a {persona} Perspective:"""

        # Estimate max_tokens (1 word ≈ 1.3 tokens, round up)
        max_tokens = int(word_length * 1.4)
        if max_tokens > 4096:
            max_tokens = 4096  # DeepSeek/ChatGPT-3.5/4 limit safeguard

        # Call DeepSeek API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error generating summary: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    try:
        with open("static/index.html") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend not found</h1><p>Please create a static/index.html file.</p>", status_code=404)

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

@app.post("/process")
async def process_form(
    search_fields: str = Form(""),
    from_date: Optional[str] = Form(None),
    limit: int = Form(10),
    categories: str = Form(""),
    sources: List[str] = Form([]),
    domains: str = Form(""),
    summarize_word_length: int = Form(1000)
):
    """Process the submitted form data and call the news API."""
    
    def split_str(value: str) -> List[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(',')]

    # Prepare parameters for the news API
    params = {
        "limit": limit,
        "extract": "true",
        "language": "en"
    }
    
    # Add search term if provided
    if search_fields:
        params["search"] = search_fields
    
    # Add categories if provided
    if categories:
        params["categories"] = categories
    
    # Add domains if provided
    if domains:
        params["domains"] = domains
    
    # Add sources if provided (convert list to comma-separated string)
    if sources:
        params["sources"] = ",".join(sources)
    
    # Add published_after date if provided
    if from_date:
        params["published_after"] = from_date
    
    try:
        # Make API call to the news endpoint
        response = requests.get("http://localhost:8000/news", params=params)
        response.raise_for_status()
        
        news_data = response.json()
        
        # Extract article data
        articles = news_data.get("articles", [])
        
        # Extract title, description, content from each article
        article_content = []
        article_urls = []
        
        for article in articles:
            # Extract title, description, and content
            article_info = {
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "content": article.get("content", "")
            }
            article_content.append(article_info)
            
            # Extract URL
            url = article.get("url", "")
            if url:
                article_urls.append(url)
        
        # Generate summary using DeepSeek API
        summary = await summarize_with_deepseek(article_content, search_fields, summarize_word_length)
        
        # Return the processed data
        return {
            "status": "success",
            "form_data": {
                "search_fields": search_fields,
                "from_date": from_date,
                "limit": limit,
                "categories": split_str(categories),
                "sources": sources,
                "domains": split_str(domains),
                "summarize_word_length": summarize_word_length
            },
            "api_params": params,
            "extracted_data": {
                "article_content": article_content,
                "article_urls": article_urls,
                "total_articles": len(articles)
            },
            "summary": summary,
            "raw_news_data": news_data
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to fetch news data: {str(e)}",
            "form_data": {
                "search_fields": search_fields,
                "from_date": from_date,
                "limit": limit,
                "categories": split_str(categories),
                "sources": sources,
                "domains": split_str(domains),
                "summarize_word_length": summarize_word_length
            },
            "api_params": params
        }

@app.get("/google-news-search")
async def google_news_search(search: str, limit: int = 10):
    """Proxy endpoint for Google News Search."""
    try:
        params = {"q": search, "limit": limit}
        response = requests.get("http://localhost:8000/search", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Failed to fetch Google News data: {str(e)}"}

@app.post("/load-news-context")
async def load_news_context(
    search_fields: str = Form(""),
    from_date: Optional[str] = Form(None),
    limit: int = Form(10),
    categories: str = Form(""),
    sources: List[str] = Form([]),
    domains: str = Form(""),
):
    """Load context from news APIs without generating summary."""
    
    def split_str(value: str) -> List[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(',')]

    # Prepare parameters for the news API
    params = {
        "limit": limit,
        "extract": "true",
        "language": "en"
    }
    
    # Add search term if provided
    if search_fields:
        params["search"] = search_fields
    
    # Add categories if provided
    if categories:
        params["categories"] = categories
    
    # Add domains if provided
    if domains:
        params["domains"] = domains
    
    # Add sources if provided (convert list to comma-separated string)
    if sources:
        params["sources"] = ",".join(sources)
    
    # Add published_after date if provided
    if from_date:
        params["published_after"] = from_date
    
    try:
        # Make API call to the news endpoint
        response = requests.get("http://localhost:8000/news", params=params)
        response.raise_for_status()
        
        news_data = response.json()
        
        # Extract article data
        articles = news_data.get("articles", [])
        
        # Extract title, description, content from each article
        article_content = []
        article_urls = []
        
        for article in articles:
            # Extract title, description, and content
            article_info = {
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "content": article.get("content", "")
            }
            article_content.append(article_info)
            
            # Extract URL
            url = article.get("url", "")
            if url:
                article_urls.append(url)
        
        # Return the extracted data without summary
        return {
            "status": "success",
            "form_data": {
                "search_fields": search_fields,
                "from_date": from_date,
                "limit": limit,
                "categories": split_str(categories),
                "sources": sources,
                "domains": split_str(domains)
            },
            "api_params": params,
            "extracted_data": {
                "article_content": article_content,
                "article_urls": article_urls,
                "total_articles": len(articles)
            },
            "raw_news_data": news_data
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to fetch news data: {str(e)}",
            "form_data": {
                "search_fields": search_fields,
                "from_date": from_date,
                "limit": limit,
                "categories": split_str(categories),
                "sources": sources,
                "domains": split_str(domains)
            },
            "api_params": params
        }

@app.post("/load-google-news-context")
async def load_google_news_context(search: str = Form(...), limit: int = Form(10)):
    """Load context from Google News without generating summary."""
    try:
        params = {"q": search, "limit": limit}
        response = requests.get("http://localhost:8000/search", params=params)
        response.raise_for_status()
        
        news_data = response.json()
        articles = news_data.get("articles", [])
        
        # Extract article data
        article_content = []
        article_urls = []
        
        for article in articles:
            article_info = {
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "content": article.get("content", "")
            }
            article_content.append(article_info)
            
            url = article.get("url", "")
            if url:
                article_urls.append(url)
        
        return {
            "status": "success",
            "form_data": {
                "search": search,
                "limit": limit
            },
            "api_params": params,
            "extracted_data": {
                "article_content": article_content,
                "article_urls": article_urls,
                "total_articles": len(articles)
            },
            "raw_news_data": news_data
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Failed to fetch Google News data: {str(e)}",
            "form_data": {
                "search": search,
                "limit": limit
            },
            "api_params": params
        }

@app.post("/condense-news")
async def condense_news(
    article_content: str = Form(...),
    search_query: str = Form(...),
    persona: str = Form(...),
    topic: str = Form(...),
    perspective: str = Form(...),
    summarize_word_length: int = Form(1000)
):
    """Generate analysis from provided article content."""
    try:
        import json
        articles = json.loads(article_content)
        summary = await summarize_with_deepseek(articles, search_query, summarize_word_length, persona, topic, perspective)
        
        return {
            "status": "success",
            "summary": summary,
            "form_data": {
                "search_query": search_query,
                "persona": persona,
                "topic": topic,
                "perspective": perspective,
                "summarize_word_length": summarize_word_length
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate analysis: {str(e)}"
        }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True) 