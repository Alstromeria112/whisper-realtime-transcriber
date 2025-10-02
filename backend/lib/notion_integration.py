"""
Notion Integration Library
Handles Notion API operations and markdown conversion
"""

import logging
import asyncio
from notion_client import Client
import time

logger = logging.getLogger(__name__)


class NotionClient:
    """Notion API client for page creation and management"""
    
    def __init__(self, token=None, parent_page_id=None):
        self.token = token
        self.parent_page_id = parent_page_id
        
        if self.token and self.parent_page_id:
            self.client = Client(auth=self.token)
            logger.info("Notion client initialized")
        else:
            self.client = None
            logger.warning("Notion token or parent page ID missing")
    
    def is_available(self):
        """Check if Notion integration is available"""
        return self.client is not None and self.parent_page_id is not None
    
    async def save_summary(self, summary_text):
        """Save summary to Notion as a new page"""
        if not self.is_available():
            return {"success": False, "message": "Notion not configured"}
        
        try:
            # Extract title from summary
            title = self._extract_title_from_summary(summary_text)
            if not title:
                title = f"Transcription Summary - {time.strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Convert markdown to Notion blocks
            blocks = self._markdown_to_notion_blocks(summary_text, skip_first_heading=True)
            
            # Create page synchronously in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self._create_page, title, blocks)
            
            return {
                "success": True,
                "url": response["url"],
                "title": title
            }
            
        except Exception as e:
            logger.error(f"Failed to save to Notion: {e}")
            return {"success": False, "message": str(e)}
    
    def _create_page(self, title, blocks):
        """Synchronously create Notion page"""
        return self.client.pages.create(
            parent={"page_id": self.parent_page_id},
            properties={
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            },
            children=blocks
        )
    
    def _markdown_to_notion_blocks(self, markdown_text, skip_first_heading=True):
        """Convert markdown text to Notion blocks with improved nested list support"""
        blocks = []
        lines = markdown_text.split('\n')
        first_heading_skipped = False
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            if line.startswith('# '):
                # Skip the first heading if it's used as page title
                if skip_first_heading and not first_heading_skipped:
                    first_heading_skipped = True
                    i += 1
                    continue
                
                # Heading 1
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": self._parse_rich_text(line[2:])
                    }
                })
            elif line.startswith('## '):
                # Heading 2
                blocks.append({
                    "object": "block", 
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": self._parse_rich_text(line[3:])
                    }
                })
            elif line.startswith('### '):
                # Heading 3
                blocks.append({
                    "object": "block",
                    "type": "heading_3", 
                    "heading_3": {
                        "rich_text": self._parse_rich_text(line[4:])
                    }
                })
            elif line.startswith('- ') or line.startswith('* '):
                # Handle bullet list with potential children
                list_item, next_index = self._parse_list_item_with_children(lines, i)
                blocks.append(list_item)
                i = next_index - 1  # -1 because loop will increment
            elif line.startswith('1. ') or line.startswith('2. ') or line.startswith('3. '):
                # Numbered list
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": self._parse_rich_text(line[3:])  # Remove "1. "
                    }
                })
            else:
                # Regular paragraph
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._parse_rich_text(line)
                    }
                })
            
            i += 1
        
        return blocks
    
    def _parse_list_item_with_children(self, lines, start_index):
        """Parse a list item and its nested children"""
        line = lines[start_index].strip()
        
        # Extract the main list item content
        if line.startswith('- '):
            main_content = line[2:]
        elif line.startswith('* '):
            main_content = line[2:]
        else:
            main_content = line
        
        # Create the main list item
        list_item = {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": self._parse_rich_text(main_content)
            }
        }
        
        # Look for nested items (children)
        children = []
        i = start_index + 1
        
        while i < len(lines):
            next_line = lines[i]
            
            # Check if this is a nested item (starts with spaces)
            if next_line.startswith('    - ') or next_line.startswith('    * '):
                # Level 2 nesting (4 spaces)
                child_content = next_line.strip()[2:]  # Remove "- " or "* "
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": self._parse_rich_text(child_content)
                    }
                })
                i += 1
            elif next_line.startswith('  - ') or next_line.startswith('  * '):
                # Level 1 nesting (2 spaces)
                child_content = next_line.strip()[2:]  # Remove "- " or "* "
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": self._parse_rich_text(child_content)
                    }
                })
                i += 1
            elif next_line.strip() == '':
                # Empty line, continue looking
                i += 1
            else:
                # Not a nested item, stop looking for children
                break
        
        # Add children if any were found
        if children:
            list_item["bulleted_list_item"]["children"] = children
        
        return list_item, i
    
    def _parse_rich_text(self, text):
        """Parse markdown-style formatting to Notion rich text"""
        import re
        
        # Initialize result array
        rich_text = []
        current_pos = 0
        
        # Pattern to match bold (**text**) and italic (*text*)
        patterns = [
            (r'\*\*([^*]+)\*\*', 'bold'),      # **bold**
            (r'\*([^*]+)\*', 'italic'),        # *italic*
            (r'`([^`]+)`', 'code'),            # `code`
        ]
        
        # Find all formatting matches
        all_matches = []
        for pattern, format_type in patterns:
            for match in re.finditer(pattern, text):
                all_matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'content': match.group(1),
                    'format': format_type,
                    'full_match': match.group(0)
                })
        
        # Sort matches by start position
        all_matches.sort(key=lambda x: x['start'])
        
        # Process text with formatting
        for match in all_matches:
            # Add plain text before this match
            if current_pos < match['start']:
                plain_text = text[current_pos:match['start']]
                if plain_text:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": plain_text}
                    })
            
            # Add formatted text
            annotations = {}
            if match['format'] == 'bold':
                annotations['bold'] = True
            elif match['format'] == 'italic':
                annotations['italic'] = True
            elif match['format'] == 'code':
                annotations['code'] = True
            
            rich_text.append({
                "type": "text",
                "text": {"content": match['content']},
                "annotations": annotations
            })
            
            current_pos = match['end']
        
        # Add remaining plain text
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            if remaining_text:
                rich_text.append({
                    "type": "text",
                    "text": {"content": remaining_text}
                })
        
        # If no formatting found, return simple text
        if not rich_text:
            rich_text = [{"type": "text", "text": {"content": text}}]
        
        return rich_text
    
    def _extract_title_from_summary(self, summary_text):
        """Extract title from Gemini summary output"""
        lines = summary_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for markdown heading (# Title)
            if line.startswith('# '):
                title = line[2:].strip()
                # Clean up title - remove common prefixes and suffixes
                title = title.replace('タイトル', '').replace('Title', '').strip()
                title = title.replace(':', '').replace('：', '').strip()
                title = title.replace('<', '').replace('>', '').strip()
                title = title.replace('タイトル名', '').strip()
                
                # Skip generic titles
                generic_titles = ['まとめ', 'Summary', '要約', 'Transcription', '文字起こし', 'Content']
                if any(generic in title for generic in generic_titles):
                    continue
                    
                if title and len(title) > 2 and len(title) < 100:  # Reasonable length
                    return title
            
            # Look for content that might be a title (first substantial line)
            if not line.startswith('#') and not line.startswith('*') and not line.startswith('-'):
                # Skip lines that look like instructions or metadata
                skip_patterns = ['以下', 'following', 'Rules', 'ルール', 'Template', 'テンプレート', '処理', 'process']
                if any(pattern in line for pattern in skip_patterns):
                    continue
                    
                if len(line) > 5 and len(line) < 80:  # Reasonable title length
                    # Remove common punctuation at the end
                    title = line.rstrip('。！？.!?:：')
                    if title:
                        return title
        
        # If no title found, return None (fallback to timestamp)
        return None
