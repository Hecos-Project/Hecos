from piper.voice import PiperVoice
print("Methods with stream:")
for item in dir(PiperVoice):
    if "stream" in item.lower() or "audio" in item.lower():
        print("  -", item)
