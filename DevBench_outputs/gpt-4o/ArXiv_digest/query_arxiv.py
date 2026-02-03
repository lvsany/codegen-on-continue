import argparse
from typing import List, Optional, Dict
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import requests
import csv

def get_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parses command-line arguments for the script."""
    parser = argparse.ArgumentParser(description="Query the ArXiv API for recent papers.")
    parser.add_argument('--category', type=str, help="Category to filter by.")
    parser.add_argument('--title', type=str, help="Title to filter by.")
    parser.add_argument('--author', type=str, help="Author to filter by.")
    parser.add_argument('--abstract', type=str, help="Abstract to filter by.")
    parser.add_argument('--max_results', type=int, default=10, help="Maximum number of results to fetch.")
    parser.add_argument('--recent_days', type=int, default=7, help="Number of recent days to filter by.")
    parser.add_argument('--output_csv', type=str, help="File name to save results as CSV.")
    parser.add_argument('--to_file', type=str, default="", help="Output file name.")
    parser.add_argument('--verbose', action='store_true', help="Enable verbose output.")
    return parser.parse_args(argv)

def construct_query_url(category: Optional[str] = None, title: Optional[str] = None, 
                        author: Optional[str] = None, abstract: Optional[str] = None, 
                        max_results: int = 10) -> str:
    """Constructs the query URL for the ArXiv API based on provided parameters."""
    base_url = "http://export.arxiv.org/api/query?"
    query_parts = []
    if category:
        query_parts.append(f"cat:{category}")
    if title:
        query_parts.append(f"ti:{title}")
    if author:
        query_parts.append(f"au:{author}")
    if abstract:
        query_parts.append(f"abs:{abstract}")
    query = '+AND+'.join(query_parts)
    return f"{base_url}search_query={query}&max_results={max_results}"

def fetch_data(query_url: str) -> bytes:
    """Fetches data from the ArXiv API using the constructed query URL."""
    response = requests.get(query_url)
    response.raise_for_status()
    return response.content

def process_entries(entries: List[ET.Element], namespace: Dict[str, str], 
                    current_date: datetime, recent_days: int) -> List[Dict[str, str]]:
    """Processes the XML entries from the ArXiv API response."""
    papers = []
    for entry in entries:
        published_date = entry.find('./default:published', namespace).text
        if check_date(published_date, recent_days, current_date):
            paper = {
                'title': entry.find('./default:title', namespace).text.strip(),
                'authors': ', '.join([author.find('./default:name', namespace).text for author in entry.findall('./default:author', namespace)]),
                'summary': entry.find('./default:summary', namespace).text.strip(),
                'abstract': entry.find('./default:summary', namespace).text.strip(),
                'published': published_date,
                'link': entry.find('./default:id', namespace).text.strip()
            }
            papers.append(paper)
    return papers

def check_date(date_string: str, recent_days: int, current_date: datetime) -> bool:
    """Checks if a paper's publication date is within the specified recent days."""
    published_date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
    return (current_date - published_date).days <= recent_days

def save_to_csv(papers: List[Dict[str, str]], file_name: str) -> None:
    """Saves the processed paper data to a CSV file."""
    if not papers:
        return
    fieldnames = list(papers[0].keys())
    with open(file_name, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(papers)

def print_results(papers: List[Dict[str, str]]) -> None:
    """Prints the processed paper data to the console."""
    for paper in papers:
        print(f"Title: {paper['title']}")
        print(f"Author(s): {paper['authors']}")
        print(f"Published: {paper['published']}")
        print(f"Summary: {paper['summary']}")
        print(f"Abstract: {paper['abstract']}")
        print(f"Link: {paper['link']}")
        print("-" * 40)

if __name__ == "__main__":
    import sys
    import os

    # Ensure the module is accessible for testing
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    # Parse arguments
    args = get_args()

    # Construct query URL
    query_url = construct_query_url(
        category=args.category,
        title=args.title,
        author=args.author,
        abstract=args.abstract,
        max_results=args.max_results
    )

    # Fetch data from ArXiv API
    try:
        data = fetch_data(query_url)
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    # Parse the XML response
    try:
        root = ET.fromstring(data)
        namespace = {'default': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('./default:entry', namespace)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        sys.exit(1)

    # Process entries
    current_date = datetime.utcnow()
    papers = process_entries(entries, namespace, current_date, args.recent_days)

    # Output results
    if args.output_csv:
        save_to_csv(papers, args.output_csv)
    else:
        print_results(papers)