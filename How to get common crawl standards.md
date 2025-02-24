# **API Guide for Standards and Content API**

# Base URL: `https://commoncrawl.alpha1edtech.com`

## **1\. Fetching Standards**

### **A. Get Standards**

```

GET /standards/items?keyword=STANDARD_CODEEXAMPLE:GET https://commoncrawl.alpha1edtech.com/standards/items?keyword=L.3.2.f
```

Example response:

```
[{
    "id": "6b99f13c-d7cc-11e8-824f-0242ac160002",
    "uri": null,
    "documentId": null,
    "CFItemType": "Component",
    "educationLevel": [
      "03"
    ],
    "CFItemTypeURI": null,
    "notes": null,
    "humanCodingScheme": "L.3.2.f",
    "listEnumeration": "f.",
    "fullStatement": "Use spelling patterns and generalizations (e.g., word families, position-based spellings, syllable patterns, ending rules, meaningful word parts) in writing words.",
    "language": "en",
    "created_at": "2025-02-18T19:15:05.739Z",
    "updated_at": "2025-02-18T19:15:05.739Z"
}]
```

## **2\. Getting Content for a CFItem**

To retrieve content associated with a CFItem (id from the previous step):

```

GET /sources/content?CFItemId={cfItemId}

```

Example response:

```

[
  {
    "id": 123,
    "type": "Article",
    "CFItemId": "789e4567-e89b-12d3-a456-426614174001",
    "name": "Understanding Addition",
    "content": {
      "title": "Basic Addition Concepts",
      "body": "Addition is a fundamental mathematical operation..."
    }
  }
]
```