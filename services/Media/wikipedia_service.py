import requests
import re
from typing import List, Dict, Optional
from urllib.parse import quote, unquote
import json

class WikipediaService:
    """Service for fetching and processing Wikipedia content"""
    
    def __init__(self):
        self.en_search_url = "https://en.wikipedia.org/w/api.php"
        self.vi_search_url = "https://vi.wikipedia.org/w/api.php"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Video-Creator/1.0 (https://example.com/contact)'
        })

    def search_articles(self, query: str, limit: int = 5, language: str = "auto") -> List[Dict]:
        """
        Search for Wikipedia articles related to the query with improved accuracy
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            language: Language to search ("en", "vi", or "auto" for automatic detection)
            
        Returns:
            List of article information with title, url, extract
        """
        try:
            # Detect language if auto
            if language == "auto":
                language = self._detect_language(query)
            
            # Choose appropriate Wikipedia API
            search_url = self.vi_search_url if language == "vi" else self.en_search_url
            
            # Try multiple search strategies for better accuracy
            search_queries = self._generate_search_variants(query, language)
            
            all_articles = []
            found_exact_match = False
            
            for search_query in search_queries:
                print(f"Trying search query: '{search_query}'")
                
                # Search for articles using Wikipedia API
                search_params = {
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': search_query,
                    'srlimit': limit * 2,  # Get more results to filter
                    'srprop': 'snippet'
                }
                
                search_response = self.session.get(search_url, params=search_params)
                search_response.raise_for_status()
                search_data = search_response.json()
                
                if 'query' in search_data and 'search' in search_data['query']:
                    print(f"Found {len(search_data['query']['search'])} raw results for '{search_query}'")
                    
                    # Score and filter results for relevance
                    scored_results = []
                    for result in search_data['query']['search']:
                        relevance_score = self._calculate_relevance_score(
                            result['title'], 
                            result.get('snippet', ''), 
                            query, 
                            search_query
                        )
                        scored_results.append((result, relevance_score))
                    
                    # Sort by relevance score (highest first)
                    scored_results.sort(key=lambda x: x[1], reverse=True)
                    
                    # Filter only highly relevant results
                    for result, score in scored_results:
                        if score >= 0.3:  # Only include results with decent relevance
                            article_info = self._get_article_info(result['title'], search_url)
                            if article_info:
                                article_info['relevance_score'] = score
                                all_articles.append(article_info)
                                print(f"Added article '{result['title']}' with score {score:.2f}")
                                
                                # Check if this is an exact match
                                if score >= 0.8:
                                    found_exact_match = True
                
                # If we found a high-quality exact match, stop searching
                if found_exact_match and all_articles:
                    break
                
                # If we have enough good results, we can stop
                if len(all_articles) >= limit:
                    break
            
            # Remove duplicates and sort by relevance
            unique_articles = []
            seen_titles = set()
            
            for article in all_articles:
                title = article.get('title', '').lower()
                if title not in seen_titles:
                    seen_titles.add(title)
                    unique_articles.append(article)
            
            # Sort by relevance score
            unique_articles.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # If no results in detected language and it's Vietnamese, try English
            if not unique_articles and language == "vi":
                return self.search_articles(query, limit, "en")
            
            return unique_articles[:limit]
            
        except Exception as e:
            print(f"Error searching Wikipedia articles: {e}")
            return []

    def _get_article_info(self, title: str, search_url: str) -> Optional[Dict]:
        """
        Get detailed information about a specific Wikipedia article
        
        Args:
            title: Article title
            search_url: The Wikipedia API URL to use
            
        Returns:
            Dictionary with article information
        """
        try:
            # Get article extract
            extract_params = {
                'action': 'query',
                'format': 'json',
                'prop': 'extracts|info',
                'exintro': True,
                'explaintext': True,
                'exsectionformat': 'plain',
                'titles': title,
                'inprop': 'url'
            }
            
            extract_response = self.session.get(search_url, params=extract_params)
            extract_response.raise_for_status()
            extract_data = extract_response.json()
            
            if 'query' in extract_data and 'pages' in extract_data['query']:
                pages = extract_data['query']['pages']
                page_id = list(pages.keys())[0]
                
                if page_id != '-1':  # Article exists
                    page = pages[page_id]
                    
                    return {
                        'title': page.get('title', ''),
                        'url': page.get('fullurl', ''),
                        'extract': self._clean_extract(page.get('extract', '')),
                        'page_id': page_id,
                        'language': 'vi' if 'vi.wikipedia' in search_url else 'en'
                    }
            
            return None
            
        except Exception as e:
            print(f"Error getting article info for '{title}': {e}")
            return None

    def _detect_language(self, text: str) -> str:
        """
        Detect if text is Vietnamese or English
        
        Args:
            text: Text to analyze
            
        Returns:
            "vi" for Vietnamese, "en" for English
        """
        # Vietnamese specific characters
        vietnamese_chars = set('àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ')
        
        # Count Vietnamese characters
        text_lower = text.lower()
        vietnamese_count = sum(1 for char in text_lower if char in vietnamese_chars)
        
        # If more than 2 Vietnamese characters, consider it Vietnamese
        return "vi" if vietnamese_count > 2 else "en"

    def _calculate_relevance_score(self, title: str, snippet: str, original_query: str, search_query: str) -> float:
        """
        Calculate relevance score for a Wikipedia article based on multiple factors
        
        Args:
            title: Article title
            snippet: Article snippet/description
            original_query: Original user query
            search_query: The specific search query variant used
            
        Returns:
            Float score between 0 and 1, where 1 is most relevant
        """
        score = 0.0
        
        # Normalize text for comparison
        title_lower = title.lower()
        snippet_lower = snippet.lower()
        original_lower = original_query.lower()
        search_lower = search_query.lower()
        
        # 1. Exact title match (highest priority)
        if title_lower == search_lower or title_lower == original_lower:
            score += 0.8
        
        # 2. Title contains full search query
        elif search_lower in title_lower:
            score += 0.6
        
        # 3. Title starts with search query (good for names)
        elif title_lower.startswith(search_lower):
            score += 0.5
        
        # 4. Search query words appear in title
        search_words = search_lower.split()
        title_words = title_lower.split()
        
        # Calculate word overlap ratio in title
        matching_words = sum(1 for word in search_words if word in title_lower)
        if search_words:
            word_match_ratio = matching_words / len(search_words)
            score += word_match_ratio * 0.4
        
        # 5. Check for name patterns (important for Vietnamese names)
        if self._is_person_name_query(original_query):
            if self._matches_person_name_pattern(title, original_query):
                score += 0.3
        
        # 6. Snippet relevance
        if snippet_lower:
            snippet_words = snippet_lower.split()
            snippet_matches = sum(1 for word in search_words if word in snippet_lower)
            if search_words:
                snippet_ratio = snippet_matches / len(search_words)
                score += snippet_ratio * 0.2
        
        # 7. Penalize disambiguation pages unless specifically looking for them
        if '(disambiguation)' in title_lower and '(disambiguation)' not in original_lower:
            score *= 0.3
        
        # 8. Boost score for exact name matches in Vietnamese
        if self._detect_language(original_query) == "vi":
            # Look for exact Vietnamese name matches
            vietnamese_names = self._extract_vietnamese_names(original_query)
            for name in vietnamese_names:
                if name.lower() in title_lower:
                    score += 0.4
                    break
        
        return min(score, 1.0)  # Cap at 1.0

    def _is_person_name_query(self, query: str) -> bool:
        """Check if the query appears to be asking about a person"""
        # Look for patterns that suggest a person name query
        name_indicators = [
            r'\b[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*',  # First Last name pattern
            r'\b(?:professor|dr|mr|mrs|ms|teacher|student)\b'  # Title indicators
        ]
        
        for pattern in name_indicators:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        
        return False
    
    def _matches_person_name_pattern(self, title: str, query: str) -> bool:
        """Check if the title matches a person name pattern from the query"""
        # Extract potential names from query
        query_names = re.findall(r'\b[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*', query)
        
        if not query_names:
            return False
        
        title_lower = title.lower()
        
        # Check if names appear in the title in any order
        name_matches = 0
        for name in query_names:
            if name.lower() in title_lower:
                name_matches += 1
        
        # Consider it a name match if most names are found
        return name_matches >= len(query_names) * 0.6
    
    def _extract_vietnamese_names(self, text: str) -> List[str]:
        """Extract Vietnamese names from text"""
        # Common Vietnamese surname patterns
        vietnamese_surnames = ['nguyễn', 'trần', 'lê', 'phạm', 'hoàng', 'huỳnh', 'phan', 'vũ', 'võ', 'đặng', 'bùi', 'đỗ', 'hồ', 'ngô', 'dương', 'lý']
        
        names = []
        
        # Look for patterns: Surname + Given names
        for surname in vietnamese_surnames:
            pattern = rf'\b{surname}\s+[a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]+\b'
            matches = re.findall(pattern, text, re.IGNORECASE)
            names.extend(matches)
        
        # Also look for capitalized word sequences (potential names)
        name_pattern = r'\b[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*(?:\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỬÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*){1,3}\b'
        potential_names = re.findall(name_pattern, text)
        names.extend(potential_names)
        
        return list(set(names))  # Remove duplicates
    
    def _generate_search_variants(self, query: str, language: str) -> List[str]:
        """
        Generate multiple search query variants to improve search accuracy
        
        Args:
            query: Original search query
            language: Language code (vi or en)
            
        Returns:
            List of search query variants, ordered by priority
        """
        variants = []
        
        # 1. Original query (cleaned)
        clean_query = self._clean_query(query, language)
        if clean_query:
            variants.append(clean_query)
        
        # 2. Try exact phrase search (in quotes)
        if len(clean_query.split()) > 1:
            variants.append(f'"{clean_query}"')
        
        # 3. Try individual meaningful words for fallback
        words = clean_query.split()
        meaningful_words = []
        
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
                     'về', 'của', 'và', 'hoặc', 'nhưng', 'trong', 'trên', 'tại', 'để', 'cho', 'với', 'bởi',
                     'create', 'make', 'video', 'tell', 'about', 'explain'}
        
        for word in words:
            if len(word) > 2 and word.lower() not in stop_words:
                meaningful_words.append(word)
        
        # 4. For person names, try different arrangements
        if self._is_person_name_query(query):
            # Try full names
            potential_names = self._extract_vietnamese_names(query) if language == "vi" else []
            for name in potential_names:
                if name not in variants:
                    variants.append(name)
            
            # Try surname only (for Vietnamese names)
            if language == "vi":
                for word in meaningful_words:
                    vietnamese_surnames = ['nguyễn', 'trần', 'lê', 'phạm', 'hoàng', 'huỳnh', 'phan', 'vũ', 'võ', 'đặng', 'bùi', 'đỗ', 'hồ', 'ngô', 'dương', 'lý']
                    if word.lower() in vietnamese_surnames:
                        # Try surname + common given names
                        common_givens = ['hoài', 'minh', 'thành', 'văn', 'thị', 'đức', 'quang', 'anh']
                        for given in common_givens:
                            if given in query.lower():
                                variants.append(f"{word} {given}")
        
        # 5. Try institution/organization names
        institution_keywords = ['university', 'college', 'school', 'institute', 'trường', 'đại học', 'học viện']
        for keyword in institution_keywords:
            if keyword.lower() in query.lower():
                # Extract the full institution name
                words_around = []
                query_words = query.split()
                for i, word in enumerate(query_words):
                    if word.lower() == keyword.lower():
                        # Get surrounding words
                        start = max(0, i-2)
                        end = min(len(query_words), i+3)
                        institution_name = ' '.join(query_words[start:end])
                        if institution_name not in variants:
                            variants.append(institution_name)
        
        # 6. Add individual meaningful words as fallback
        for word in meaningful_words:
            if len(word) > 3 and word not in variants:
                variants.append(word)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for variant in variants:
            if variant.lower() not in seen and variant.strip():
                seen.add(variant.lower())
                unique_variants.append(variant.strip())
        
        return unique_variants[:8]  # Limit to top 8 variants

    def _clean_query(self, query: str, language: str) -> str:
        """Clean and optimize query for Wikipedia search"""
        # Language-specific stop words
        if language == "vi":
            stop_words = {'và', 'của', 'trong', 'với', 'từ', 'cho', 'về', 'tại', 'này', 'đó', 'một', 'các', 'những', 
                         'được', 'có', 'là', 'không', 'thì', 'sẽ', 'đã', 'khi', 'nếu', 'mà', 'để', 'như', 'theo',
                         'tạo', 'video', 'nội dung', 'viết', 'kịch bản', 'ngắn', 'câu chuyện', 'giải thích', 'mô tả'}
        else:
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                         'create', 'make', 'video', 'content', 'generate', 'write', 'script', 'short', 'story', 
                         'tell', 'me', 'about', 'explain', 'describe'}
        
        # Extract meaningful keywords
        if language == "vi":
            # For Vietnamese, keep whole words including names
            words = re.findall(r'[a-zA-ZàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ]+', query)
        else:
            words = re.findall(r'\b\w+\b', query.lower())
        
        meaningful_words = []
        for word in words:
            word_lower = word.lower()
            if (len(word) > 2 and 
                word_lower not in stop_words and 
                not word.isdigit()):
                meaningful_words.append(word)
        
        return ' '.join(meaningful_words[:5])  # Limit to 5 most relevant words

    def _clean_extract(self, extract: str) -> str:
        """Clean and truncate article extract"""
        if not extract:
            return ""
        
        # Remove excessive whitespace and newlines
        cleaned = re.sub(r'\s+', ' ', extract.strip())
        
        # Truncate to reasonable length (around 200 words)
        words = cleaned.split()
        if len(words) > 200:
            cleaned = ' '.join(words[:200]) + '...'
        
        return cleaned

    def get_relevant_content(self, topic: str, max_articles: int = 3, model: str = "deepseek") -> Dict:
        """
        Get relevant Wikipedia content for a topic
        
        Args:
            topic: The topic to search for
            max_articles: Maximum number of articles to return
            model: AI model to use for keyword extraction ("deepseek" or "gemini")
            
        Returns:
            Dictionary containing articles and summary content
        """
        try:
            # First try with the full topic
            articles = self.search_articles(topic, limit=max_articles, language="auto")
            
            # If no results, try alternative search strategies
            if not articles:
                # Strategy 1: Use AI to extract better keywords
                keywords = self.extract_keywords_with_ai(topic, model)
                print(f"AI extracted keywords for search using {model}: {keywords}")
                
                for keyword in keywords:
                    if keyword:
                        print(f"Trying search with AI keyword: {keyword}")
                        articles = self.search_articles(keyword, limit=max_articles, language="auto")
                        if articles:
                            print(f"Found {len(articles)} articles for AI keyword: {keyword}")
                            break
            
            # If still no results, try searching individual words
            if not articles:
                words = topic.split()
                for word in words:
                    if len(word) > 3:  # Only try meaningful words
                        print(f"Trying search with word: {word}")
                        articles = self.search_articles(word, limit=max_articles, language="auto")
                        if articles:
                            print(f"Found {len(articles)} articles for word: {word}")
                            break
            
            # Create a summary of all relevant content
            all_content = []
            sources = []
            
            for article in articles:
                if article and article.get('extract'):
                    all_content.append(article['extract'])
                    sources.append({
                        'title': article['title'],
                        'url': article['url'],
                        'extract': article['extract'][:300] + '...' if len(article['extract']) > 300 else article['extract'],
                        'language': article.get('language', 'en')
                    })
            
            # Combine content for context
            combined_content = '\n\n'.join(all_content)
            
            return {
                'sources': sources,
                'combined_content': combined_content,
                'topic': topic,
                'found_articles': len(sources)
            }
            
        except Exception as e:
            print(f"Error getting relevant content for '{topic}': {e}")
            return {
                'sources': [],
                'combined_content': '',
                'topic': topic,
                'found_articles': 0
            }

    def extract_keywords_with_ai(self, prompt: str, model: str = "deepseek") -> List[str]:
        """
        Use AI to extract the most relevant Wikipedia search keywords from a prompt
        
        Args:
            prompt: User prompt
            model: AI model to use ("deepseek" or "gemini")
            
        Returns:
            List of AI-suggested keywords for Wikipedia search
        """
        try:
            # Create AI prompt for keyword extraction
            keyword_prompt = f"""
You are an expert at analyzing text prompts and identifying the most relevant keywords for Wikipedia searches.

Given this user prompt: "{prompt}"

Extract 2-3 most relevant keywords that would be best for searching Wikipedia articles. Focus on:
1. Person names (full names like "Lê Hoài Bắc")
2. Institution names (like "HCMUS", "Harvard University")
3. Specific topics or subjects
4. Important concepts or entities

Ignore common words like: create, video, script, about, tell, explain, etc.

Return ONLY the keywords separated by commas, nothing else.

Examples:
- Input: "Create a video about Lê Hoài Bắc HCMUS teacher"
- Output: Lê Hoài Bắc, HCMUS

- Input: "Tell me about artificial intelligence and machine learning"  
- Output: artificial intelligence, machine learning

Your response for "{prompt}":
"""
            
            # Use the specified AI model
            if model.lower() == "gemini":
                # Use Gemini model
                from google import genai
                from config.app_config import GEMINI_KEY
                
                client = genai.Client(api_key=GEMINI_KEY)
                
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[keyword_prompt],  
                )
                ai_content = response.text
                
                print(f"Using Gemini for keyword extraction: {ai_content}")
            else:
                # Use DeepSeek model (default)
                from openai import OpenAI
                from config.app_config import OPENROUTER_KEY

                client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=OPENROUTER_KEY,
                )
                
                completion = client.chat.completions.create(
                    extra_body={},
                    model="deepseek/deepseek-chat-v3-0324:free",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": keyword_prompt,
                                },
                            ]    
                        }
                    ],
                )
                
                ai_content = completion.choices[0].message.content
                print(f"Using DeepSeek for keyword extraction: {ai_content}")
            
            # Extract keywords from AI response
            # Look for the actual keyword list (usually the last line or after specific patterns)
            lines = ai_content.strip().split('\n')
            keywords_line = ""
            
            # Find the line that looks like keywords (contains commas or is the last non-empty line)
            for line in reversed(lines):
                line = line.strip()
                if line and not line.startswith('Input:') and not line.startswith('Output:') and not line.startswith('Examples:'):
                    if ',' in line or len(lines) == 1:
                        keywords_line = line
                        break
            
            if not keywords_line:
                # Fallback: take the last non-empty line
                for line in reversed(lines):
                    if line.strip():
                        keywords_line = line.strip()
                        break
            
            # Clean and split keywords
            if keywords_line:
                # Remove any remaining instructional text
                keywords_line = re.sub(r'^(Output:|Keywords?:|Response:)', '', keywords_line, flags=re.IGNORECASE).strip()
                keywords_line = re.sub(r'^[^:]*:', '', keywords_line).strip()  # Remove any "something:" prefix
                
                keywords = [kw.strip() for kw in keywords_line.split(',') if kw.strip()]
                
                # Filter out any remaining instructional words
                filter_words = {'input', 'output', 'example', 'examples', 'your', 'response', 'for', 'keywords'}
                keywords = [kw for kw in keywords if kw.lower() not in filter_words and len(kw) > 1]
                
                print(f"AI extracted keywords using {model}: {keywords}")
                return keywords[:3]  # Return top 3 keywords
            
            # If AI extraction fails, fallback to simple extraction
            print(f"AI keyword extraction with {model} failed, falling back to simple method")
            return self.extract_keywords_from_prompt_simple(prompt)
            
        except Exception as e:
            print(f"Error in AI keyword extraction with {model}: {e}")
            # Fallback to simple extraction
            return self.extract_keywords_from_prompt_simple(prompt)

    def extract_keywords_from_prompt_simple(self, prompt: str) -> List[str]:
        """
        Simple fallback method for keyword extraction
        """
        # Detect language
        language = self._detect_language(prompt)
        
        keywords = []
        
        # Look for proper names (capitalized words)
        name_patterns = [
            r'\b([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỬÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*(?:\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỬÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]*){1,3})\b',
            r'\b([A-Z]{2,})\b'  # Acronyms
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, prompt)
            for match in matches:
                if match and len(match.strip()) > 1:
                    keywords.append(match.strip())
        
        return keywords[:3]
