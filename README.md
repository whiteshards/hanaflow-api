
# Anime & Manga API

A FastAPI-based API for fetching anime and manga data from various sources.

## Overview

This API provides endpoints to search, browse, and fetch detailed information about anime and manga from different sources. Currently supported sources:

- **Anime**: Hanime
- **Manga**: Comick, NHentai

## API Endpoints

### Anime Endpoints

#### 1. Search/Browse Anime

First, use one of the following endpoints to get a list of anime:

- **Search by Query**:
  ```
  GET /api/anime/search?q={query}&source=hanime&page=1&limit=20
  ```

- **Get Popular Anime**:
  ```
  GET /api/anime/popular?source=hanime&page=1&limit=20
  ```

- **Get Latest Anime**:
  ```
  GET /api/anime/latest?source=hanime&page=1&limit=20
  ```

**Response Structure**:
```json
{
  "totalResults": 100,
  "page": 1,
  "limit": 20,
  "source": "hanime",
  "query": "search term",
  "results": [
    {
      "id": "/videos/hentai/anime-slug",
      "title": "Anime Title [Hanime]",
      "url": "/videos/hentai/anime-slug",
      "poster": "https://example.com/image.jpg",
      "description": "Anime description",
      "author": "Studio Name",
      "genres": "Tag1, Tag2, Tag3",
      "source": "hanime"
    },
    // More results...
  ],
  "executionTimeMs": 500
}
```

#### 2. Get Anime Details

Using the ID/URL from the previous step, fetch detailed information including all episodes:

```
GET /api/anime/details?source=hanime&id=/videos/hentai/anime-slug
```

**Response Structure**:
```json
{
  "title": "Anime Title",
  "url": "/videos/hentai/anime-slug",
  "poster": "https://example.com/image.jpg",
  "description": "Full description of the anime",
  "author": "Studio Name",
  "genres": "Tag1, Tag2, Tag3",
  "info": {
    "Studio": "Studio Name"
  },
  "episodes": [
    {
      "title": "Episode 1",
      "episode": 1,
      "url": "https://hanime.tv/api/v8/video?id=12345",
      "date": 1609459200000,
      "source": "hanime"
    },
    // More episodes...
  ],
  "executionTimeMs": 300
}
```

#### 3. Get Episode Streaming Links

Finally, use the episode URL to get streaming links:

```
GET /api/anime/get-episode?source=hanime&id=https://hanime.tv/api/v8/video?id=12345
```

**Response Structure**:
```json
{
  "source": "hanime",
  "id": "https://hanime.tv/api/v8/video?id=12345",
  "episode_url": "https://hanime.tv/api/v8/video?id=12345",
  "streams": [
    {
      "url": "https://example.com/video/1080p.mp4",
      "quality": "1080p"
    },
    {
      "url": "https://example.com/video/720p.mp4",
      "quality": "720p"
    },
    // More quality options...
  ],
  "executionTimeMs": 200
}
```

### Manga Endpoints

#### 1. Search/Browse Manga

- **Search by Query**:
  ```
  GET /api/manga/search?q={query}&source=comick&page=1&limit=20
  ```

- **Get Popular Manga**:
  ```
  GET /api/manga/popular?source=comick&page=1&limit=20
  ```

- **Get Latest Manga**:
  ```
  GET /api/manga/latest?source=comick&page=1&limit=20
  ```

#### 2. Get Manga Details

```
GET /api/manga/details?source=comick&id=manga-slug
```

#### 3. Get Manga Pages

```
GET /api/manga/get-pages?source=comick&id=chapter-id
```

### Additional Endpoints

#### Get Available Filters

```
GET /api/filters?source=hanime
```

## Complete Workflow Example

### Anime Workflow

1. **First Request**: Search for anime or get popular/latest anime to get a list of anime items
   ```
   GET /api/anime/search?q=love&source=hanime&page=1&limit=20
   ```

2. **Second Request**: Get details for a specific anime using its ID/URL to obtain the episode list
   ```
   GET /api/anime/details?source=hanime&id=/videos/hentai/anime-slug
   ```

3. **Third Request**: Get streaming links for a specific episode using its URL
   ```
   GET /api/anime/get-episode?source=hanime&id=https://hanime.tv/api/v8/video?id=12345
   ```

### Manga Workflow

1. **First Request**: Search for manga or get popular/latest manga
   ```
   GET /api/manga/search?q=romance&source=comick&page=1&limit=20
   ```

2. **Second Request**: Get details for a specific manga
   ```
   GET /api/manga/details?source=comick&id=manga-slug
   ```

3. **Third Request**: Get pages for a specific chapter
   ```
   GET /api/manga/get-pages?source=comick&id=chapter-id
   ```

## Notes

- All endpoints support pagination with `page` and `limit` parameters
- The `source` parameter specifies which source to use (currently supported: `hanime`, `comick`, `nhentai`)
- The API calculates execution time which is included in all responses

## Running the API

To run the API locally:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

The API documentation will be available at `/docs`.
