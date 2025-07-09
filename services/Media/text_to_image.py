def generate_image(model, prompt,style=None, output_file="image.png", width=720, height=1280):
    style_prompts = {
        "ghibli": "in the style of Studio Ghibli, anime, beautiful, detailed, magical, whimsical",
        "watercolor": "watercolor painting, soft colors, artistic, painted with watercolors, gentle brushstrokes",
        "manga": "manga style, black and white, detailed lineart, Japanese comic book art",
        "pixar": "Pixar animation style, 3D rendered, colorful, cartoon, Disney Pixar movie",
        "scifi": "sci-fi art, futuristic, cyberpunk, neon colors, high-tech, space age",
        "oilpainting": "oil painting, classical art, renaissance style, detailed brushwork, rich colors",
        "dark": "dark art, gothic, mysterious, dramatic lighting, shadows, moody atmosphere",
        "lego": "LEGO style, made of LEGO bricks, blocky, colorful plastic bricks",
        "realistic": "photorealistic, highly detailed, professional photography, 8k resolution",
        "cartoon": "cartoon style, colorful, fun, animated, simple shapes",
        "vintage": "vintage style, retro, old-fashioned, sepia tones, classic",
        "minimalist": "minimalist art, simple, clean lines, geometric, modern",
        "fantasy": "fantasy art, magical, mystical, dragons, medieval, epic fantasy",
        "popart": "pop art style, bright colors, Andy Warhol inspired, bold graphics",
        "impressionist": "impressionist painting, soft brushstrokes, light and color, Monet style"
    }
    if style and style.lower() in style_prompts:
        prompt = f"{prompt}, {style_prompts[style.lower()]}"
    if model == "flux":
        import base64
        from PIL import Image
        from io import BytesIO
        from together import Together
        from config import TOGETHER_KEY

        """Generate image from text prompt using Together AI"""
        client = Together(api_key=TOGETHER_KEY)
        
        response = client.images.generate(
            prompt=prompt,
            model="black-forest-labs/FLUX.1-schnell-Free",
            width=width,
            height=height,
            steps=4,
            n=1,
            response_format="b64_json",
        )
        
        # Decode and save image
        image_data = base64.b64decode(response.data[0].b64_json)
        image = Image.open(BytesIO(image_data))
        image.save(output_file)
        
        return output_file
    elif model == "gemini":
        """Generate image from text prompt using Google Gemini"""
        from PIL import Image
        from io import BytesIO
        from google import genai
        from google.genai import types
        from PIL import Image
        from io import BytesIO
        import base64
        from config import GEMINI_KEY

        client = genai.Client(api_key=GEMINI_KEY)

        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=prompt,
            config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE']
            )
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image = Image.open(BytesIO((part.inline_data.data)))
                # Save the image to the current path with the name "image.png"
                image.save(output_file)
                
                return output_file