"""
Script to grab a list of open "add wiki" issues from GitHub
"""
import requests
import pandas as pd
import re

ISSUE_BODY_REGEX = re.compile(r"""(?:An anonymous user has submitted a new wiki via our \[submission form\]\([^\)]+\)\.\n*
)?Link to origin wiki:\s*((?:.|\n)*)
Link to destination \((?:independent|official)\) wiki:\s*(.*)(?:\n|$)""")


def parse_link_header(raw_link_header):
    # Split into pieces and extract their components
    link_header_matches = [re.match(r'\<(.*)\>; rel="(\w+)"', value.strip()) for value in raw_link_header.split(",")]

    # Format as a dict
    return {entry.group(2): entry.group(1) for entry in link_header_matches}


def github_api_request(api_url, params):
    results_pages = []
    more_pages = True
    while more_pages:
        response = requests.get(api_url, params=params)

        # If the URL returned an HTTP error, raise an exception
        if not response:
            response.raise_for_status()

        # Add the results to the list
        results_pages.append(response.json())

        # Check if there are more results
        link_headers = parse_link_header(response.headers["link"])
        if "next" in link_headers:
            api_url = link_headers["next"]
            params = {}  # The URL from the link header has all the necessary parameters included
        else:
            more_pages = False

    return results_pages


def get_add_wiki_issues():
    gh_api_url = "https://api.github.com/repos/KevinPayravi/indie-wiki-buddy/issues"
    params = {"accept": "application/vnd.github.raw+json", "labels": "add wiki", "per_page": "100"}
    results_pages = github_api_request(gh_api_url, params)

    df = pd.concat([pd.DataFrame(page) for page in results_pages])

    # Drop all Pull Requests
    if "pull_request" in df.columns:
        df = df[df["pull_request"].isna()]

    # Use the issue number as the index
    df = df.set_index("number")

    return df


def parse_github_wiki_body(df):
    body_series = df["body"].copy()

    # Normalize line breaks (GitHub seems to use \r\n anyway, but just in case that can vary)
    body_series = body_series.str.replace("\r\n", "\n")
    # Remove display text from Markdown links
    body_series = body_series.str.replace(r"\[((?:.|\n)*?)\]\((https?://.*?)\)", r"\2", regex=True)

    # Extract the URLs from the issue body
    body_df: pd.DataFrame = body_series.str.extract(ISSUE_BODY_REGEX)
    body_df.columns = ["origin", "destination"]
    body_df["origin"] = body_df["origin"].apply(parse_origin_wiki_value)
    body_df["destination"] = body_df["destination"].apply(parse_singular_wiki_value)
    # Valid requests can only have a single destination. If multiple are specified, do not parse it.

    return body_df


def parse_singular_wiki_value(wiki_value):
    """
    Strips any comments from a single entry in a "Link to origin wiki" or "Link to destination (independent) wiki" field
    """
    if pd.isna(wiki_value):
        return wiki_value

    wiki_value = wiki_value.strip()

    # Strip any text after the first space (this is presumed to be a comment)
    if " " in wiki_value:
        wiki_value = wiki_value.split(" ")[0]

    # If the URL has a trailing comma, it was not pre-processed correctly
    if wiki_value.endswith(","):
        return None

    return wiki_value


def parse_origin_wiki_value(wiki_value):
    """
    Parses the value of "Link to origin wiki" to get a list of wiki URLs
    """
    # If null, don't do anything
    if pd.isna(wiki_value):
        return wiki_value

    # If there are multiple URLs, treat each as a separate entry
    url_match = re.findall(r"https?://.*?(?:\s|$)", wiki_value)
    if len(url_match) > 1:
        # Remove trailing commas in case of comma-separated lists
        url_list = [parse_singular_wiki_value(url.strip().removesuffix(",")) for url in url_match]
        return url_list

    # Otherwise, there is only one entry in the input
    return [parse_singular_wiki_value(wiki_value)]


def main():
    add_wiki_issues_df = get_add_wiki_issues()
    body_df = parse_github_wiki_body(add_wiki_issues_df)

    output_df = pd.concat([add_wiki_issues_df, body_df], axis=1).copy()

    # Log and drop any entries that failed to parse
    failed_entries = output_df[output_df["destination"].isna()]
    for index, entry in failed_entries.iterrows():
        print(f'Failed to parse Issue #{index} "{entry.title}": {entry.html_url}')
    output_df = output_df[output_df["destination"].notna()]

    # Explode the origins column, as it is a list of URLs
    output_df = output_df.explode("origin")

    # Write selected columns to CSV
    csv_filename = "pending_requests.csv"
    output_df = output_df[["origin", "destination", "title", "html_url", "created_at"]]
    output_df.to_csv(csv_filename)
    print(f"Wrote to {csv_filename}")


if __name__ == "__main__":
    main()
