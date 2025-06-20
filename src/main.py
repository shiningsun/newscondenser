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

async def summarize_with_deepseek(article_content: List[Dict], search_query: str) -> str:
    """Summarize articles using DeepSeek API."""
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
        
        # Create the prompt for summarization
        prompt = f"""Based on the news articles provided below, which are the search results for '{search_query}', please write a comprehensive 1000-word summary of all the events related to this topic. Your summary should use the content of these articles as the primary source of information to construct a coherent narrative. The goal is to produce a single, detailed overview that synthesizes the information from all articles, not to summarize each article individually.

Search Query: "{search_query}"

Articles:
{context}

Please structure your summary to:
1.  Create a cohesive narrative of events and developments related to "{search_query}".
2.  Synthesize key information, facts, and figures from the articles.
3.  Provide context and background where necessary to explain the significance of the events.
4.  Maintain a neutral and objective tone throughout the summary.
5.  Be approximately 1000 words long.

Comprehensive Summary of Events Related to "{search_query}":"""

        # Call DeepSeek API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
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
    domains: str = Form("")
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
        summary = await summarize_with_deepseek(article_content, search_fields)
        
        # Return the processed data
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
                "domains": split_str(domains)
            },
            "api_params": params
        }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True) 