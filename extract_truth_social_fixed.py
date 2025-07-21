#!/usr/bin/env python3

import json
from typing import List, Dict, Any
from bs4 import BeautifulSoup

def extract_truth_social_posts(html_file_path: str) -> List[Dict[str, Any]]:
    """Extract Truth Social posts from the exact div structure shown"""
    
    print(f"🔍 Reading HTML file: {html_file_path}")
    
    with open(html_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    print("📝 Parsing with lxml...")
    soup = BeautifulSoup(content, 'lxml')
    
    # Find the exact post containers: class="block mb-8 rounded-xl border border-[#2F3C4B]/20"
    post_containers = soup.find_all('div', class_=lambda x: x and 'block' in x and 'mb-8' in x and 'rounded-xl' in x and 'border' in x)
    
    print(f"📊 Found {len(post_containers)} post containers with the target class pattern")
    
    if len(post_containers) == 0:
        # Fallback - look for any divs with block mb-8
        post_containers = soup.find_all('div', class_=lambda x: x and isinstance(x, list) and 'block' in x and 'mb-8' in x)
        print(f"📊 Fallback: Found {len(post_containers)} containers with 'block mb-8'")
    
    posts = []
    
    for i, container in enumerate(post_containers):
        try:
            post_data = extract_post_from_container(container)
            
            if post_data.get('content_text') or post_data.get('speaker'):
                posts.append(post_data)
                
                if len(posts) % 25 == 0:
                    print(f"✅ Extracted {len(posts)} posts so far...")
        except Exception as e:
            print(f"❌ Error extracting post {i+1}: {e}")
            continue
    
    return posts

def extract_post_from_container(container) -> Dict[str, Any]:
    """Extract all data from a single post container"""
    
    post_data = {}
    
    # Extract speaker name - look for font-bold divs with actual text
    speaker_divs = container.find_all('div', class_=lambda x: x and 'font-bold' in str(x))
    for div in speaker_divs:
        speaker_text = div.get_text(strip=True)
        # Get the actual rendered text, skip empty/template text
        if speaker_text and len(speaker_text) > 2 and len(speaker_text) < 50:
            if not speaker_text.startswith('x-text') and 'item.' not in speaker_text:
                post_data['speaker'] = speaker_text
                break
    
    # Extract handle - look for spans containing @username
    all_spans = container.find_all('span')
    for span in all_spans:
        span_text = span.get_text(strip=True)
        if span_text.startswith('@') and len(span_text) > 3 and len(span_text) < 30:
            post_data['handle'] = span_text
            break
    
    # Extract date - look for spans with ET timezone
    for span in all_spans:
        span_text = span.get_text(strip=True)
        if 'ET' in span_text and '@' in span_text and any(month in span_text for month in [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]):
            post_data['date'] = span_text
            break
    
    # Extract platform - look for "Truth Social" or "Twitter" text
    for span in all_spans:
        span_text = span.get_text(strip=True)
        if span_text == 'Truth Social':
            post_data['platform'] = 'Truth Social'
            break
        elif span_text == 'Twitter' or span_text == 'X':
            post_data['platform'] = 'Twitter'
            break
    
    # If no platform found in text, check icons
    if not post_data.get('platform'):
        if container.find('img', src=lambda x: x and 'truthsocial.png' in str(x)):
            post_data['platform'] = 'Truth Social'
        elif container.find('i', class_=lambda x: x and 'fa-x-twitter' in str(x)):
            post_data['platform'] = 'Twitter'
        else:
            post_data['platform'] = 'Unknown'
    
    # Extract post URL
    post_links = container.find_all('a', href=True)
    for link in post_links:
        href = link.get('href', '')
        if 'truthsocial.com' in href and '/posts/' in href:
            post_data['post_url'] = href
            if not post_data.get('platform') or post_data.get('platform') == 'Unknown':
                post_data['platform'] = 'Truth Social'
            break
        elif ('twitter.com' in href or 'x.com' in href) and '/status/' in href:
            post_data['post_url'] = href
            if not post_data.get('platform') or post_data.get('platform') == 'Unknown':
                post_data['platform'] = 'Twitter'
            break
    
    # Extract content text from whitespace-pre-wrap divs
    content_divs = container.find_all('div', class_=lambda x: x and 'whitespace-pre-wrap' in str(x))
    for div in content_divs:
        content_text = div.get_text(strip=True)
        if content_text and len(content_text) > 10:
            post_data['content_text'] = content_text
            post_data['content_html'] = str(div)
            
            # Extract links from content
            content_links = div.find_all('a', href=True)
            if content_links:
                post_data['content_links'] = [
                    {'url': link.get('href', ''), 'text': link.get_text(strip=True)} 
                    for link in content_links if link.get('href')
                ]
            break
    
    # Extract image URL
    images = container.find_all('img')
    for img in images:
        src = img.get('src', '')
        # Skip icons, get actual media images
        if src and not src.endswith('truthsocial.png') and not 'unavatar.io' in src:
            if 'media-cdn.factba.se' in src:
                post_data['image_url'] = src
                break
    
    # Check for deleted flag
    deleted_spans = container.find_all('span', class_=lambda x: x and 'text-red-500' in str(x))
    post_data['deleted_flag'] = any('Deleted' in span.get_text() for span in deleted_spans)
    
    return post_data

def print_results(posts):
    """Print formatted extraction results"""
    print(f"\n{'='*70}")
    print(f"🎯 TRUTH SOCIAL EXTRACTION RESULTS")
    print(f"{'='*70}")
    
    if not posts:
        print("❌ No posts found!")
        return
    
    print(f"📊 Total posts extracted: {len(posts)}")
    
    # Count metadata completeness
    complete_posts = 0
    speakers_found = 0
    handles_found = 0
    dates_found = 0
    urls_found = 0
    platforms_found = 0
    
    platforms = {}
    speakers = {}
    
    for post in posts:
        if post.get('speaker'): speakers_found += 1
        if post.get('handle'): handles_found += 1
        if post.get('date'): dates_found += 1
        if post.get('post_url'): urls_found += 1
        if post.get('platform') and post.get('platform') != 'Unknown': platforms_found += 1
        
        # Count as complete if has speaker, handle, and content
        if post.get('speaker') and post.get('handle') and post.get('content_text'):
            complete_posts += 1
        
        platform = post.get('platform', 'Unknown')
        platforms[platform] = platforms.get(platform, 0) + 1
        
        speaker = post.get('speaker', 'Unknown')
        speakers[speaker] = speakers.get(speaker, 0) + 1
    
    print(f"\n📈 Metadata Extraction Success Rate:")
    print(f"   ✅ Complete posts (speaker + handle + content): {complete_posts}/{len(posts)} ({complete_posts/len(posts)*100:.1f}%)")
    print(f"   👤 Speakers found: {speakers_found}/{len(posts)} ({speakers_found/len(posts)*100:.1f}%)")
    print(f"   📱 Handles found: {handles_found}/{len(posts)} ({handles_found/len(posts)*100:.1f}%)")
    print(f"   📅 Dates found: {dates_found}/{len(posts)} ({dates_found/len(posts)*100:.1f}%)")
    print(f"   🔗 URLs found: {urls_found}/{len(posts)} ({urls_found/len(posts)*100:.1f}%)")
    print(f"   🌐 Platforms identified: {platforms_found}/{len(posts)} ({platforms_found/len(posts)*100:.1f}%)")
    
    print(f"\n🔍 Platform Breakdown:")
    for platform, count in platforms.items():
        print(f"   {platform}: {count} posts")
    
    print(f"\n👥 Top Speakers:")
    for speaker, count in list(speakers.items())[:7]:
        print(f"   {speaker}: {count} posts")
    
    # Show sample posts
    print(f"\n📝 Sample Posts:")
    print("-" * 70)
    
    # Show posts with best metadata first
    sample_posts = sorted(posts[:5], key=lambda p: (
        bool(p.get('speaker')), 
        bool(p.get('handle')), 
        bool(p.get('date')), 
        bool(p.get('post_url'))
    ), reverse=True)
    
    for i, post in enumerate(sample_posts):
        print(f"\n🔹 POST {i+1}:")
        print(f"   Speaker: {post.get('speaker', 'N/A')}")
        print(f"   Handle: {post.get('handle', 'N/A')}")
        print(f"   Platform: {post.get('platform', 'N/A')}")
        print(f"   Date: {post.get('date', 'N/A')}")
        print(f"   Deleted: {'Yes' if post.get('deleted_flag') else 'No'}")
        
        content = post.get('content_text', 'N/A')
        if len(content) > 150:
            content = content[:150] + "..."
        print(f"   Content: {content}")
        
        if post.get('post_url'):
            print(f"   🔗 URL: {post['post_url']}")
        if post.get('image_url'):
            print(f"   📷 Image: Yes")
        if post.get('content_links'):
            print(f"   🔗 Links in content: {len(post['content_links'])}")

def main():
    html_file = 'full.html'
    output_file = 'report/data/truth_social_posts_final.json'
    
    try:
        posts = extract_truth_social_posts(html_file)
        
        if posts:
            # Save to JSON
            print(f"\n💾 Saving {len(posts)} posts to {output_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)
            
            # Print results
            print_results(posts)
            
            print(f"\n{'='*70}")
            print(f"🎉 SUCCESS! Extraction completed!")
            print(f"📂 Results saved to: {output_file}")
            print(f"📊 Extracted {len(posts)} posts with metadata!")
            print(f"{'='*70}")
            
        else:
            print("❌ No posts extracted. Check the HTML structure.")
            
    except FileNotFoundError:
        print(f"❌ Error: HTML file '{html_file}' not found")
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 