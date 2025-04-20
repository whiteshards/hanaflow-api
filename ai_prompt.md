
# Anime & Manga API Usage Guide

This API allows you to search, browse, and fetch anime and manga data from various sources. Here's how to use it:

## Sources

The API currently supports the following sources:
- **Anime**: Hanime, HahoMoe
- **Manga**: Comick, NHentai

## Basic Workflow

To fetch content:
1. **First**: Get a list of anime/manga using search, popular, or latest endpoints
2. **Second**: Get details for a specific item using its ID from the first response
3. **Third**: Get episodes/chapters for anime/manga (usually included in details response)
4. **Optional**: Get streaming links for a specific anime episode

## Endpoints for Anime

### 1. Browse Anime

Use one of these endpoints to get a list of anime:

```
GET /api/anime/search?q=your_query&source=hahomoe&page=1&limit=20
GET /api/anime/popular?source=hahomoe&page=1&limit=20
GET /api/anime/latest?source=hahomoe&page=1&limit=20
```

### 2. Get Anime Details

Using an ID from the previous step:
```
GET /api/anime/details?source=hahomoe&id=/videos/anime-title
```

### 3. Get Episode Streaming Links

Using an episode URL from the details:
```
GET /api/anime/get-episode?source=hahomoe&id=https://source.com/episode/123
```

## Endpoints for Manga

### 1. Browse Manga

Use one of these endpoints to get a list of manga:

```
GET /api/manga/search?q=your_query&source=comick&page=1&limit=20
GET /api/manga/popular?source=comick&page=1&limit=20
GET /api/manga/latest?source=comick&page=1&limit=20
```

### 2. Get Manga Details

Using an ID from the previous step:
```
GET /api/manga/details?source=comick&id=manga-slug
```

### 3. Get Manga Pages

Using a chapter ID from the details:
```
GET /api/manga/get-pages?source=comick&id=chapter-id
```

## Filters

Get available filters for a source:
```
GET /api/filters?source=hahomoe
```

## Response Structure

Responses follow a consistent format with metadata and content:
- `totalResults`: Total number of results available
- `page`: Current page number
- `limit`: Number of results per page
- `source`: The source being queried
- `results`: List of items (anime/manga)
- `executionTimeMs`: API execution time in milliseconds

## Example Usage Flow

1. Search for anime:
   ```
   GET /api/anime/search?q=romance&source=hahomoe&page=1&limit=20
   ```

2. Get details for a specific anime:
   ```
   GET /api/anime/details?source=hahomoe&id=/videos/romance-anime
   ```

3. Get streaming links for an episode:
   ```
   GET /api/anime/get-episode?source=hahomoe&id=https://haho.moe/episode/12345
   ```

The API handles pagination automatically and provides structured responses with all the necessary information to navigate through content.
