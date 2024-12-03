"""Web search utilities for Fiber."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple
import re
from dataclasses import dataclass
from rich.console import Console

console = Console()

@dataclass
class SearchResult:
    url: str
    title: str
    description: str
    relevance_score: float = 0.0

def get_google_results(query: str, num_results: int = 5) -> List[SearchResult]:
    """Get search results from Google."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        url = f'https://www.google.com/search?q={quote_plus(query)}&num={num_results}'
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for div in soup.find_all('div', class_='g'):
            try:
                title_elem = div.find('h3')
                link_elem = div.find('a')
                desc_elem = div.find('div', class_='VwiC3b')
                
                if title_elem and link_elem and desc_elem:
                    title = title_elem.text
                    url = link_elem['href']
                    description = desc_elem.text
                    
                    if url.startswith('http'):
                        results.append(SearchResult(url, title, description))
            except Exception:
                continue
                
        return results
    except Exception as e:
        console.print(f"[yellow]Warning: Google search failed: {str(e)}[/yellow]")
        return []

def get_bing_results(query: str, num_results: int = 5) -> List[SearchResult]:
    """Get search results from Bing."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        url = f'https://www.bing.com/search?q={quote_plus(query)}&count={num_results}'
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for li in soup.find_all('li', class_='b_algo'):
            try:
                title_elem = li.find('h2')
                link_elem = title_elem.find('a') if title_elem else None
                desc_elem = li.find('div', class_='b_caption')
                
                if title_elem and link_elem and desc_elem:
                    title = title_elem.text
                    url = link_elem['href']
                    description = desc_elem.text
                    
                    if url.startswith('http'):
                        results.append(SearchResult(url, title, description))
            except Exception:
                continue
                
        return results
    except Exception as e:
        console.print(f"[yellow]Warning: Bing search failed: {str(e)}[/yellow]")
        return []

def get_duckduckgo_results(query: str, num_results: int = 5) -> List[SearchResult]:
    """Get search results from DuckDuckGo."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        url = f'https://html.duckduckgo.com/html/?q={quote_plus(query)}'
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for div in soup.find_all('div', class_='result'):
            try:
                title_elem = div.find('a', class_='result__a')
                desc_elem = div.find('a', class_='result__snippet')
                
                if title_elem and desc_elem:
                    title = title_elem.text
                    url = title_elem['href']
                    description = desc_elem.text
                    
                    if url.startswith('http'):
                        results.append(SearchResult(url, title, description))
                        
                        if len(results) >= num_results:
                            break
            except Exception:
                continue
                
        return results
    except Exception as e:
        console.print(f"[yellow]Warning: DuckDuckGo search failed: {str(e)}[/yellow]")
        return []

def calculate_relevance_score(result: SearchResult, query: str) -> float:
    """Calculate relevance score for a search result."""
    score = 0.0
    query_terms = set(query.lower().split())
    
    # Check title relevance
    title_terms = set(result.title.lower().split())
    title_matches = len(query_terms.intersection(title_terms))
    score += title_matches * 2.0  # Title matches are weighted more heavily
    
    # Check description relevance
    desc_terms = set(result.description.lower().split())
    desc_matches = len(query_terms.intersection(desc_terms))
    score += desc_matches
    
    # Bonus for exact phrase matches
    if query.lower() in result.title.lower():
        score += 3.0
    if query.lower() in result.description.lower():
        score += 2.0
    
    # URL relevance
    url_terms = set(re.split(r'[/.-]', result.url.lower()))
    url_matches = len(query_terms.intersection(url_terms))
    score += url_matches * 1.5
    
    return score

def get_best_result(query: str) -> Tuple[SearchResult, str]:
    """Get the most relevant search result from all search engines."""
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Start all searches in parallel
        future_google = executor.submit(get_google_results, query)
        future_bing = executor.submit(get_bing_results, query)
        future_ddg = executor.submit(get_duckduckgo_results, query)
        
        # Collect all results
        all_results = []
        sources = []
        
        for future, source in [(future_google, "Google"), 
                             (future_bing, "Bing"), 
                             (future_ddg, "DuckDuckGo")]:
            try:
                results = future.result()
                for result in results:
                    result.relevance_score = calculate_relevance_score(result, query)
                    all_results.append(result)
                    sources.append(source)
            except Exception as e:
                console.print(f"[yellow]Warning: {source} search failed: {str(e)}[/yellow]")
    
    if not all_results:
        raise Exception("No search results found from any search engine")
    
    # Find the most relevant result
    best_result = max(all_results, key=lambda x: x.relevance_score)
    best_source = sources[all_results.index(best_result)]
    
    return best_result, best_source

def open_in_chrome(url: str):
    """Open URL in Chrome browser."""
    try:
        # Try to use Chrome specifically
        chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
        webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
        webbrowser.get('chrome').open(url)
    except Exception:
        # Fallback to default browser if Chrome is not available
        webbrowser.open(url)
