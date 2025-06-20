def get_prompt(prompt) -> str:
    return (f"""
You are a content generator for short-form videos under 60 seconds.

Given a single user prompt in any language, you must:
1. Detect the language of the prompt
2. Write the video **title** and **script** in the same language as the user prompt, should be either English or Vietnamese
3. Write exactly 3 **image generation prompts** in English that visually illustrate key moments of the script

The script should be short and engaging, and take no more than 60 seconds to read aloud (maximum ~120 words).

Return the result strictly in the following JSON format:
{{
  "title": "....",
  "script": "....",
  "image_prompts": [
    "...",
    "...",
    "..."
  ]
}}

User prompt: {prompt}
""")

def generate_text(model, prompt):
    if (model=="deepseek"):
        from openai import OpenAI
        from config import OPENROUTER_KEY

        # Initialize the OpenAI client
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_KEY,
        )
        
        # Generate text using the OpenAI API
        completion = client.chat.completions.create(
            extra_body={},
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": get_prompt(prompt),
                        },
                    ]    
                }
            ],
        )
        return completion.choices[0].message.content
    
    elif (model=="gemini"):
        from google import genai
        from config import GEMINI_KEY
        from google.genai import types

        client = genai.Client(api_key=GEMINI_KEY)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[get_prompt(prompt)],  
        )
        return response.text

def generate_image_prompts_from_script(script_text: str, count: int = 3) -> list:
    """
    Generate image prompts from script text for background generation
    """
    try:
        import json
        
        prompt = f"""
You are an expert at creating visual prompts for AI image generation.

Given a video script, generate {count} distinct image prompts in English that would make good background scenes for this video.

Each prompt should:
1. Describe a visual scene that complements the script content
2. Be detailed enough for AI image generation
3. Focus on backgrounds/environments rather than characters
4. Be visually distinct from each other

Return the result strictly in JSON format:
{{
  "image_prompts": [
    "prompt 1",
    "prompt 2", 
    "prompt 3"
  ]
}}

Script: {script_text}
"""
        
        # Use the existing generate_text function with deepseek model
        response = generate_text("deepseek", prompt)
        
        # Parse the JSON response
        result = json.loads(response)
        return result.get("image_prompts", [])
        
    except Exception as e:
        print(f"Error generating image prompts from script: {e}")
        # Fallback: return simple prompts based on script keywords
        return [
            f"Background scene for: {script_text[:50]}...",
            f"Environment setting for: {script_text[:50]}...",
            f"Visual backdrop for: {script_text[:50]}..."
        ][:count]
