---
name: Smart Search
description: Executes a DuckDuckGo search and returns a JSON list of results.
author: Satele's Brain
parameters:
  - name: query
    type: string
    description: The search query.
    required: true
---

## Description

This skill allows the agent to perform web searches using DuckDuckGo. It returns a JSON list of the top results, including titles and URLs.  Handles request errors and JSON decoding errors.

## Tools

```tool_code
python3 .agent/skills/smart_search/smart_search.py "SEARCH_QUERY"
```

Example:
```tool_code
python3 .agent/skills/smart_search/smart_search.py "What is the capital of France?"
```