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
from manga_scrapers.comick import ComickScraper # Added ComickScraper import


def main_menu():
    """Display the main menu and handle user interaction"""
    haho_moe_searcher = HahoMoeSearcher()
    ani_zone_searcher = AniZoneSearcher()
    all_anime_searcher = AllAnimeScraper()
    hanime_searcher = HanimeScraper() # Added Hanime scraper initialization
    comick_searcher = ComickScraper() # Added ComickScraper initialization

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
        print("6. Search manga on Comick") # Added Comick manga search option
        print("7. Set Hanime Quality Preference") # Added Hanime quality setting option
        print("8. Exit") # Updated exit option number

        try:
            choice = input("\nEnter your choice (1-8): ") # Updated choice range

            if choice in ['1', '2', '3', '4', '5', '6', '7', '8']:
                if choice == '8':
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
                        
                    if choice == '1' or choice == '5':
                        hanime_results = hanime_searcher.search_anime(query)
                        all_results.extend(hanime_results)
                        print(f"Found {len(hanime_results)} results from Hanime")

                    if choice == '5':
                        # Hanime search submenu
                        print("\nHanime Search Options:")
                        print("1. Basic Search")
                        print("2. Manage Tag Filters")
                        print("3. Manage Production Company Filters")
                        print("4. Set Tag Mode (AND/OR)")
                        print("5. Set Sort Order")
                        print("6. Clear All Filters")
                        print("7. Go Back")

                        hanime_choice = input("\nEnter your choice (1-7): ")

                        if hanime_choice == '1':
                            # Use the already entered search query instead of asking again
                            results = hanime_searcher.search_anime(query)
                            all_results = results 
                            source = 'hanime'
                        elif hanime_choice == '2':
                            # Tag management submenu
                            print("\nManage Tag Filters:")
                            print("Enter tag name and state (1=include, 0=neutral, -1=exclude)")
                            print("Available tags:")

                            # Display tags in multiple columns
                            tags = hanime_searcher.get_tags()
                            for i, tag in enumerate(tags):
                                print(f"{i+1}. {tag['name']}", end="\t")
                                if (i+1) % 5 == 0:  # 5 columns
                                    print()
                            print("\n")

                            tag_idx = input("Enter tag number or name (or 0 to cancel): ")
                            if tag_idx == '0':
                                continue

                            try:
                                if tag_idx.isdigit() and 1 <= int(tag_idx) <= len(tags):
                                    tag_name = tags[int(tag_idx)-1]['name']
                                else:
                                    tag_name = tag_idx

                                state = int(input("Enter state (1=include, 0=neutral, -1=exclude): "))
                                if -1 <= state <= 1:
                                    hanime_searcher.set_tag_filter(tag_name, state)
                                else:
                                    print("Invalid state. Please use 1, 0, or -1.")
                            except Exception as e:
                                print(f"Error setting tag filter: {e}")
                            continue

                        elif hanime_choice == '3':
                            # Production company management submenu
                            print("\nManage Production Company Filters:")
                            print("Available production companies:")

                            # Display companies in multiple columns
                            companies = hanime_searcher.get_brands()
                            for i, company in enumerate(companies):
                                if i < 100:  # Limit display to avoid overwhelming console
                                    print(f"{i+1}. {company['name']}", end="\t")
                                    if (i+1) % 3 == 0:  # 3 columns
                                        print()
                            print("\n(Showing first 100 companies)")
                            print("\n")

                            company_idx = input("Enter company number or name (or 0 to cancel): ")
                            if company_idx == '0':
                                continue

                            try:
                                if company_idx.isdigit() and 1 <= int(company_idx) <= len(companies):
                                    company_name = companies[int(company_idx)-1]['id']
                                else:
                                    company_name = company_idx

                                enabled = input("Enable filter? (y/n): ").lower() == 'y'
                                hanime_searcher.set_brand_filter(company_name, enabled)
                            except Exception as e:
                                print(f"Error setting company filter: {e}")
                            continue

                        elif hanime_choice == '4':
                            # Tag mode setting
                            print("\nSet Tag Mode:")
                            print("1. AND (all tags must match)")
                            print("2. OR (any tag can match)")

                            mode_choice = input("Enter your choice (1-2): ")
                            if mode_choice == '1':
                                hanime_searcher.set_tag_mode("AND")
                            elif mode_choice == '2':
                                hanime_searcher.set_tag_mode("OR")
                            else:
                                print("Invalid choice.")
                            continue

                        elif hanime_choice == '5':
                            # Sort order setting
                            print("\nSet Sort Order:")
                            sort_options = hanime_searcher.get_sortable_list()
                            for i, option in enumerate(sort_options):
                                print(f"{i+1}. {option[0]}")

                            sort_choice = input(f"Enter your choice (1-{len(sort_options)}): ")
                            if sort_choice.isdigit() and 1 <= int(sort_choice) <= len(sort_options):
                                direction = input("Sort ascending? (y/n): ").lower() == 'y'
                                option_idx = int(sort_choice) - 1
                                hanime_searcher.set_sort_order(sort_options[option_idx][1], direction)
                            else:
                                print("Invalid choice.")
                            continue

                        elif hanime_choice == '6':
                            # Clear all filters
                            hanime_searcher.clear_filters()
                            print("All filters have been reset.")
                            continue

                        elif hanime_choice == '7':
                            # Go back to main menu
                            continue

                        else:
                            print("Invalid choice.")
                            continue


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
                    # Comick Manga search
                    query = input("\nEnter manga title to search: ")
                    if not query.strip():
                        print("Please enter a valid search term.")
                        continue
                    
                    print(f"\n🔍 Searching for '{query}' on Comick...")
                    manga_results = comick_searcher.search_manga(query)
                    
                    if not manga_results:
                        print("No results found. Try a different search term.")
                        continue
                    
                    # Display search results
                    print(f"\nFound {len(manga_results)} manga results:")
                    for i, manga in enumerate(manga_results, 1):
                        title = manga.get('title', 'Unknown Title')
                        print(f"{i}. {title}")
                    
                    # Let user select a manga
                    while True:
                        try:
                            selection = input("\nEnter the number of the manga to view details (or 0 to go back): ")
                            if selection == '0':
                                break
                            
                            selection_idx = int(selection) - 1
                            if 0 <= selection_idx < len(manga_results):
                                selected_manga = manga_results[selection_idx]
                                
                                # Get manga details
                                print(f"\nFetching details for {selected_manga.get('title', 'Unknown Title')}...")
                                manga_details = comick_searcher.get_manga_details(selected_manga)
                                
                                if manga_details:
                                    # Display manga details
                                    print(f"\n{'=' * 50}")
                                    print(f"Manga Details: {manga_details.get('title', 'Unknown Title')} [Comick]")
                                    print(f"{'=' * 50}")
                                    
                                    # Display cover
                                    if 'cover_url' in manga_details and manga_details['cover_url']:
                                        print(f"\nCover URL: {manga_details['cover_url']}")
                                    
                                    # Display description
                                    if 'description' in manga_details and manga_details['description']:
                                        print(f"\nDescription:")
                                        display_description = manga_details['description']
                                        if len(display_description) > 300:
                                            display_description = display_description[:300] + "..."
                                        print(display_description)
                                    
                                    # Display additional info
                                    if 'info' in manga_details and manga_details['info']:
                                        print("\nAdditional Information:")
                                        for key, value in manga_details['info'].items():
                                            print(f"   {key}: {value}")
                                    
                                    # Display genres if available
                                    if 'genres' in manga_details and manga_details['genres']:
                                        print(f"\nGenres: {', '.join(manga_details['genres'])}")
                                    
                                    print(f"{'=' * 50}")
                                    
                                    # Get chapters
                                    print(f"\nFetching chapters...")
                                    chapters = comick_searcher.get_chapters(manga_details)
                                    
                                    if not chapters:
                                        print("No chapters found for this manga.")
                                        continue
                                    
                                    # Display chapters
                                    print(f"\nFound {len(chapters)} chapters:")
                                    
                                    # Calculate how many chapters to show initially
                                    chapter_limit = 10
                                    limited_display = len(chapters) > chapter_limit
                                    display_chapters = chapters[:chapter_limit] if limited_display else chapters
                                    
                                    for i, chapter in enumerate(display_chapters, 1):
                                        print(f"{i}. {chapter.get('title', f'Chapter {chapter.get('chapter_number', i)}')}")
                                    
                                    if limited_display:
                                        print(f"...and {len(chapters) - chapter_limit} more chapters.")
                                    
                                    # Let user select a chapter
                                    while True:
                                        try:
                                            ch_selection = input("\nEnter the number of the chapter to view pages (or 0 to go back, or 'all' to see all chapters): ")
                                            
                                            if ch_selection.lower() == 'all':
                                                # Show all chapters
                                                print(f"\nShowing all {len(chapters)} chapters:")
                                                for i, chapter in enumerate(chapters, 1):
                                                    print(f"{i}. {chapter.get('title', f'Chapter {chapter.get('chapter_number', i)}')}")
                                                continue
                                            
                                            if ch_selection == '0':
                                                break
                                            
                                            ch_idx = int(ch_selection) - 1
                                            if 0 <= ch_idx < len(chapters):
                                                selected_chapter = chapters[ch_idx]
                                                
                                                # Get chapter pages
                                                print(f"\nFetching pages for {selected_chapter.get('title', f'Chapter {selected_chapter.get('chapter_number', ch_idx+1)}')}...")
                                                pages = comick_searcher.get_pages(selected_chapter.get('id', ''))
                                                
                                                if not pages:
                                                    print("No pages found for this chapter.")
                                                    continue
                                                
                                                # Display page info
                                                print(f"\nFound {len(pages)} pages.")
                                                print("Page URLs have been saved to urls.txt")
                                                
                                                # Write page URLs to file
                                                with open('urls.txt', 'a') as url_file:
                                                    url_file.write(f"\n==== Comick: {manga_details.get('title', 'Unknown Manga')} - {selected_chapter.get('title', f'Chapter {selected_chapter.get('chapter_number', ch_idx+1)}')} ====\n")
                                                    for i, page in enumerate(pages, 1):
                                                        url_file.write(f"Page {i}: {page.get('url', 'No URL')}\n")
                                            else:
                                                print("Invalid chapter number. Please try again.")
                                        except ValueError:
                                            print("Please enter a valid number.")
                                        except Exception as e:
                                            print(f"An error occurred while fetching/displaying pages: {e}")
                                            continue
                                else:
                                    print("Failed to get manga details.")
                            else:
                                print("Invalid selection. Please try again.")
                        except ValueError:
                            print("Please enter a valid number.")
                        except Exception as e:
                            print(f"An error occurred while selecting manga: {e}")
                            continue
                
                elif choice == '7':
                    try:
                        quality = input("Enter desired Hanime quality (e.g., 720p, 1080p): ")
                        hanime_searcher.set_quality(quality)
                        print(f"Hanime quality preference set to: {quality}")
                    except Exception as e:
                        print(f"Error setting Hanime quality: {e}")
            else:
                print("Invalid choice. Please enter a number between 1 and 8.") # Updated range
        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            continue

if __name__ == "__main__":
    main_menu()