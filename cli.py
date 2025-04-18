import requests
from bs4 import BeautifulSoup
import cloudscraper
import sys
import time
import urllib.parse
import os
import re
import json

# Importing our scrapers
from scrapers.hahomoe_scraper import HahoMoeSearcher
from scrapers.anizone_scraper import AniZoneSearcher
from scrapers.allanime_scraper import AllAnimeScraper
from scrapers.hanime_scraper import HanimeScraper # Added Hanime scraper import


def main_menu():
    """Display the main menu and handle user interaction"""
    haho_moe_searcher = HahoMoeSearcher()
    ani_zone_searcher = AniZoneSearcher()
    all_anime_searcher = AllAnimeScraper()
    hanime_searcher = HanimeScraper() # Added Hanime scraper initialization

    print("""
        ####################################
        ##   Anime Search Tool            ##
        ##   (Educational Purposes Only)  ##
        ####################################
        """)

    while True:
        print("\nWhat would you like to do?")
        print("1. Search for anime (All Sources)")
        print("2. Search on HahoMoe only")
        print("3. Search on AniZone only")
        print("4. Search on AllAnime only")
        print("5. Search on Hanime only") # Added Hanime search option
        print("6. Set Hanime Quality Preference") # Added Hanime quality setting option
        print("7. Exit") # Updated exit option number

        try:
            choice = input("\nEnter your choice (1-7): ") # Updated choice range

            if choice in ['1', '2', '3', '4', '5', '6', '7']:
                if choice == '7':
                    print("Exiting...")
                    break

                if choice in ['1', '2', '3', '4', '5']:
                    query = input("\nEnter anime title to search: ")
                    if not query.strip():
                        print("Please enter a valid search term.")
                        continue

                    all_results = []

                    if choice == '1' or choice == '2':
                        haho_moe_results = haho_moe_searcher.search_anime(query)
                        all_results.extend(haho_moe_results)
                        print(f"Found {len(haho_moe_results)} results from HahoMoe.")

                    if choice == '1' or choice == '3':
                        ani_zone_results = ani_zone_searcher.search_anime(query)
                        all_results.extend(ani_zone_results)
                        print(f"Found {len(ani_zone_results)} results from AniZone")

                    if choice == '1' or choice == '4':
                        all_anime_results = all_anime_searcher.search_anime(query)
                        all_results.extend(all_anime_results)
                        print(f"Found {len(all_anime_results)} results from AllAnime")

                    if choice == '5':
                        search_query = input("Enter search query for Hanime: ")
                        results = hanime_searcher.search_anime(search_query)
                        all_results = results #Update all_results
                        source = 'hanime' # Set source for hanime


                    if not all_results:
                        print("No results found. Try a different search term.")
                        continue

                    # Display search results
                    print(f"\nFound {len(all_results)} total results:")
                    for i, result in enumerate(all_results, 1):
                        print(f"{i}. {result.get('title')}")


                    # Let user select an anime
                    while True:
                        try:
                            selection = input("\nEnter the number of the anime to view details (or 0 to go back): ")
                            if selection == '0':
                                break

                            selection_idx = int(selection) - 1
                            if 0 <= selection_idx < len(all_results):
                                selected_anime = all_results[selection_idx]

                                # Get source type
                                source = selected_anime.get('source', '')


                                # Get anime details from appropriate source
                                anime_details = None
                                if source == 'hahomoe':
                                    anime_details = haho_moe_searcher.get_anime_details(selected_anime['url'])
                                elif source == 'anizone':
                                    anime_details = ani_zone_searcher.get_anime_details(selected_anime['url'])
                                elif source == 'allanime':
                                    anime_details = all_anime_searcher.get_anime_details(selected_anime['url'])
                                elif source == 'hanime':
                                    anime_details = hanime_searcher.get_anime_details(selected_anime['url']) # Added hanime
                                else:
                                    print(f"Unknown source: {source}")
                                    continue

                                if anime_details:
                                    # Display anime details
                                    print(f"\n{'=' * 50}")
                                    source_tag = f"[{source.capitalize()}]" if source else ""
                                    print(f"Anime Details: {anime_details.get('title', 'Unknown Title')} {source_tag}")
                                    print(f"{'=' * 50}")

                                    # Display poster
                                    if 'poster' in anime_details and anime_details['poster'] and anime_details['poster'] != "No poster available":
                                        print(f"\nPoster URL: {anime_details['poster']}")

                                    # Display description
                                    if 'description' in anime_details and anime_details['description']:
                                        print(f"\nDescription:")
                                        # Limit description length for display
                                        display_description = anime_details['description']
                                        if len(display_description) > 300:
                                            display_description = display_description[:300] + "..."
                                        print(display_description)


                                    # Display additional info
                                    if 'info' in anime_details and anime_details['info']:
                                        print("\nAdditional Information:")
                                        for key, value in anime_details['info'].items():
                                            print(f"   {key}: {value}") # Added colon for clarity

                                    # Display genres if available
                                    if 'genres' in anime_details and anime_details['genres']: # Added check for empty genres
                                        print(f"\nGenres: {anime_details['genres']}")

                                    print(f"{'=' * 50}")

                                    # Get episodes from appropriate source
                                    print(f"\nFetching episodes...")
                                    episodes = []

                                    if source == 'hahomoe':
                                        episodes = haho_moe_searcher.get_episodes(anime_details)
                                    elif source == 'anizone':
                                        episodes = ani_zone_searcher.get_episodes(anime_details)
                                    elif source == 'allanime':
                                        episodes = all_anime_searcher.get_episodes(anime_details)
                                    elif source == 'hanime':
                                        episodes = hanime_searcher.get_episodes(anime_details) # Added hanime
                                    else:
                                        print(f"Unknown source: {source}")
                                        continue

                                    if not episodes:
                                        print("No episodes found for this anime.")
                                        # Allow going back to anime selection if no episodes
                                        continue # Changed break to continue

                                    # Display episodes
                                    print(f"\nFound {len(episodes)} episodes:")

                                    # Calculate how many episodes to show initially
                                    episode_limit = 10
                                    limited_display = len(episodes) > episode_limit
                                    display_episodes = episodes[:episode_limit] if limited_display else episodes

                                    for i, ep in enumerate(display_episodes, 1):
                                        print(f"{i}. {ep.get('title')}")

                                    if limited_display:
                                        print(f"...and {len(episodes) - episode_limit} more episodes.")

                                    # Let user select an episode
                                    while True:
                                        try:
                                            ep_selection = input("\nEnter the number of the episode to get streams (or 0 to go back, or 'all' to see all episodes): ")

                                            if ep_selection.lower() == 'all':
                                                # Show all episodes
                                                print(f"\nShowing all {len(episodes)} episodes:")
                                                for i, ep in enumerate(episodes, 1):
                                                    print(f"{i}. {ep.get('title')}")
                                                continue

                                            if ep_selection == '0':
                                                # Allow going back to anime details from episode selection
                                                break # Changed continue to break

                                            ep_idx = int(ep_selection) - 1
                                            if 0 <= ep_idx < len(episodes):
                                                selected_episode = episodes[ep_idx]

                                                # Get video streams from appropriate source
                                                print(f"\nFetching video streams for {selected_episode.get('title')}...")
                                                video_streams = []

                                                if source == 'hahomoe':
                                                    video_streams = haho_moe_searcher.get_video_sources(selected_episode['url'])
                                                elif source == 'anizone':
                                                    video_streams = ani_zone_searcher.get_video_sources(selected_episode['url'])
                                                elif source == 'allanime':
                                                    # Note: AllAnime get_video_sources expects the JSON payload stored in 'url'
                                                    video_streams = all_anime_searcher.get_video_sources(selected_episode['url'])
                                                elif source == 'hanime':
                                                    video_streams = hanime_searcher.get_video_sources(selected_episode['url']) # Added hanime
                                                else:
                                                    print(f"Unknown source: {source}")
                                                    continue

                                                if not video_streams:
                                                    print("No video streams found for this episode.")
                                                    continue

                                                # Display available streams
                                                print(f"\nFound {len(video_streams)} video streams:")
                                                for i, stream in enumerate(video_streams, 1):
                                                    # Ensure 'quality' and 'url' keys exist before accessing
                                                    quality = stream.get('quality', 'Unknown Quality')
                                                    url = stream.get('url', 'No URL')
                                                    print(f"{i}. {quality} - {url[:75]}...")

                                                print("\nStreams have been saved to urls.txt")
                                                # After displaying streams, go back to episode selection
                                                continue # Added continue to go back to episode selection menu
                                            else:
                                                print("Invalid episode number. Please try again.")
                                        except ValueError:
                                            print("Please enter a valid number.")
                                        except Exception as e:
                                            print(f"An error occurred while fetching/displaying streams: {e}")
                                            # Continue to episode selection menu on error
                                            continue # Added continue
                                else:
                                    print("Failed to get anime details.")
                            else:
                                print("Invalid selection. Please try again.")
                        except ValueError:
                            print("Please enter a valid number.")
                        except Exception as e:
                            print(f"An error occurred while selecting anime: {e}")
                            # Continue to anime selection menu on error
                            continue # Added continue
                elif choice == '6':
                    try:
                        quality = input("Enter desired Hanime quality (e.g., 720p, 1080p): ")
                        hanime_searcher.set_quality(quality)
                        print(f"Hanime quality preference set to: {quality}")
                    except Exception as e:
                        print(f"Error setting Hanime quality: {e}")
            else:
                print("Invalid choice. Please enter a number between 1 and 7.") # Updated range
        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            continue

if __name__ == "__main__":
    main_menu()