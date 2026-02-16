import os
import sys
import subprocess
from datetime import datetime

def run_speedtest():
    """Run speedtest using CLI and create a visual result image"""
    
    print("🚀 Starting speed test...")
    
    # Find speedtest-cli in venv
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    speedtest_cmd = os.path.join(project_root, "venv", "bin", "speedtest-cli")
    
    # Run speedtest-cli
    try:
        result = subprocess.run(
            [speedtest_cmd, "--simple"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"Error running speedtest: {result.stderr}")
            return
        
        # Parse results
        lines = result.stdout.strip().split('\n')
        ping = download = upload = "N/A"
        
        for line in lines:
            if line.startswith("Ping:"):
                ping = line.split(":")[1].strip()
            elif line.startswith("Download:"):
                download = line.split(":")[1].strip()
            elif line.startswith("Upload:"):
                upload = line.split(":")[1].strip()
        
        # Create a simple text result
        result_text = f"""
╔════════════════════════════════════╗
║      SPEEDTEST RESULTS             ║
╠════════════════════════════════════╣
║                                    ║
║  📡 Ping:     {ping:20s} ║
║  ⬇️  Download: {download:20s} ║
║  ⬆️  Upload:   {upload:20s} ║
║                                    ║
║  Tested: {datetime.now().strftime("%Y-%m-%d %H:%M:%S"):20s} ║
║                                    ║
╚════════════════════════════════════╝
"""
        
        # Print to console
        print(result_text)
        
        # Also create an image using PIL if available, otherwise just return text
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create image
            img = Image.new('RGB', (600, 400), color=(30, 30, 40))
            draw = ImageDraw.Draw(img)
            
            # Try to use a nice font, fallback to default
            try:
                font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
                font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
                font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Draw title
            draw.text((300, 40), "SPEEDTEST RESULTS", fill=(100, 200, 255), anchor="mm", font=font_large)
            
            # Draw results
            y_offset = 120
            draw.text((80, y_offset), "📡 Ping:", fill=(200, 200, 200), font=font_medium)
            draw.text((520, y_offset), ping, fill=(255, 255, 255), anchor="rm", font=font_medium)
            
            y_offset += 70
            draw.text((80, y_offset), "⬇️  Download:", fill=(200, 200, 200), font=font_medium)
            draw.text((520, y_offset), download, fill=(100, 255, 100), anchor="rm", font=font_medium)
            
            y_offset += 70
            draw.text((80, y_offset), "⬆️  Upload:", fill=(200, 200, 200), font=font_medium)
            draw.text((520, y_offset), upload, fill=(255, 200, 100), anchor="rm", font=font_medium)
            
            # Draw timestamp
            draw.text((300, 350), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                     fill=(150, 150, 150), anchor="mm", font=font_small)
            
            # Save image
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
            media_dir = os.path.join(project_root, "media")
            os.makedirs(media_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"speedtest_{timestamp}.png"
            screenshot_path = os.path.join(media_dir, filename)
            
            img.save(screenshot_path)
            print(f"UPLOAD:{screenshot_path}")
            
        except ImportError:
            # PIL not available, just return text
            print("Note: Install Pillow for graphical results: pip install Pillow")
            print(f"\n📊 Results:\nPing: {ping}\nDownload: {download}\nUpload: {upload}")
            
    except subprocess.TimeoutExpired:
        print("Error: Speed test timed out after 60 seconds")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_speedtest()
