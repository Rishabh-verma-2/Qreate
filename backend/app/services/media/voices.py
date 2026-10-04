"""Curated voice catalog (Microsoft Edge neural voices — free, no key).

Each language lists several voices with a short "vibe" so creators can pick by
ear (the UI plays a preview). `NON_LATIN` languages skip uppercase captions.
"""

from typing import Dict, List, Optional

# language → (sample line for previews, [(voice_id, display name, gender, accent/vibe)])
CATALOG: Dict[str, Dict] = {
    "English": {
        "sample": "Hey! This is the voice of your next viral reel. Ready?",
        "voices": [
            ("en-US-AndrewMultilingualNeural", "Andrew", "male", "US · warm, confident storyteller"),
            ("en-US-BrianMultilingualNeural", "Brian", "male", "US · casual, energetic creator"),
            ("en-US-AvaMultilingualNeural", "Ava", "female", "US · expressive, friendly"),
            ("en-US-EmmaMultilingualNeural", "Emma", "female", "US · cheerful, conversational"),
            ("en-US-GuyNeural", "Guy", "male", "US · bold, news-style"),
            ("en-US-JennyNeural", "Jenny", "female", "US · bright, upbeat"),
            ("en-US-ChristopherNeural", "Christopher", "male", "US · deep, documentary"),
            ("en-US-MichelleNeural", "Michelle", "female", "US · calm, polished"),
            ("en-GB-RyanNeural", "Ryan", "male", "British · dramatic, cinematic"),
            ("en-GB-SoniaNeural", "Sonia", "female", "British · elegant"),
            ("en-GB-ThomasNeural", "Thomas", "male", "British · smooth"),
            ("en-AU-WilliamMultilingualNeural", "William", "male", "Australian · laid-back"),
            ("en-AU-NatashaNeural", "Natasha", "female", "Australian · lively"),
            ("en-IN-PrabhatNeural", "Prabhat", "male", "Indian English · friendly"),
            ("en-IN-NeerjaExpressiveNeural", "Neerja", "female", "Indian English · expressive"),
        ],
    },
    "Hinglish": {
        "sample": "Hey yaar! Ye hai tumhari next viral reel ki awaaz. Chalo shuru karte hain!",
        "voices": [
            ("en-IN-NeerjaExpressiveNeural", "Neerja", "female", "expressive, Gen Z"),
            ("en-IN-PrabhatNeural", "Prabhat", "male", "friendly, relatable"),
            ("en-IN-NeerjaNeural", "Neerja Classic", "female", "clear, steady"),
        ],
    },
    "Hindi": {
        "sample": "नमस्ते! ये आपकी अगली वायरल रील की आवाज़ है। चलिए शुरू करते हैं!",
        "voices": [
            ("hi-IN-MadhurNeural", "Madhur", "male", "warm, storyteller"),
            ("hi-IN-SwaraNeural", "Swara", "female", "bright, friendly"),
            ("en-US-AvaMultilingualNeural", "Ava (multilingual)", "female", "soft, modern"),
            ("en-US-AndrewMultilingualNeural", "Andrew (multilingual)", "male", "deep, modern"),
        ],
    },
    "Marathi": {
        "sample": "नमस्कार! हा तुमच्या पुढच्या व्हायरल रीलचा आवाज आहे.",
        "voices": [("mr-IN-ManoharNeural", "Manohar", "male", "warm"), ("mr-IN-AarohiNeural", "Aarohi", "female", "bright")],
    },
    "Tamil": {
        "sample": "வணக்கம்! இது உங்கள் அடுத்த வைரல் ரீலின் குரல்.",
        "voices": [("ta-IN-ValluvarNeural", "Valluvar", "male", "warm"), ("ta-IN-PallaviNeural", "Pallavi", "female", "bright")],
    },
    "Telugu": {
        "sample": "నమస్కారం! ఇది మీ తదుపరి వైరల్ రీల్ వాయిస్.",
        "voices": [("te-IN-MohanNeural", "Mohan", "male", "warm"), ("te-IN-ShrutiNeural", "Shruti", "female", "bright")],
    },
    "Bengali": {
        "sample": "নমস্কার! এটা আপনার পরের ভাইরাল রিলের কণ্ঠ।",
        "voices": [("bn-IN-BashkarNeural", "Bashkar", "male", "warm"), ("bn-IN-TanishaaNeural", "Tanishaa", "female", "bright")],
    },
    "Gujarati": {
        "sample": "નમસ્તે! આ તમારી આગામી વાયરલ રીલનો અવાજ છે.",
        "voices": [("gu-IN-NiranjanNeural", "Niranjan", "male", "warm"), ("gu-IN-DhwaniNeural", "Dhwani", "female", "bright")],
    },
    "Kannada": {
        "sample": "ನಮಸ್ಕಾರ! ಇದು ನಿಮ್ಮ ಮುಂದಿನ ವೈರಲ್ ರೀಲ್‌ನ ಧ್ವನಿ.",
        "voices": [("kn-IN-GaganNeural", "Gagan", "male", "warm"), ("kn-IN-SapnaNeural", "Sapna", "female", "bright")],
    },
    "Malayalam": {
        "sample": "നമസ്കാരം! ഇത് നിങ്ങളുടെ അടുത്ത വൈറൽ റീലിന്റെ ശബ്ദമാണ്.",
        "voices": [("ml-IN-MidhunNeural", "Midhun", "male", "warm"), ("ml-IN-SobhanaNeural", "Sobhana", "female", "bright")],
    },
    "Urdu": {
        "sample": "السلام علیکم! یہ آپ کی اگلی وائرل ریل کی آواز ہے۔",
        "voices": [("ur-IN-SalmanNeural", "Salman", "male", "warm"), ("ur-IN-GulNeural", "Gul", "female", "soft")],
    },
    "Spanish": {
        "sample": "¡Hola! Esta es la voz de tu próximo reel viral.",
        "voices": [
            ("es-ES-AlvaroNeural", "Álvaro", "male", "Spain · confident"),
            ("es-ES-ElviraNeural", "Elvira", "female", "Spain · warm"),
            ("es-MX-JorgeNeural", "Jorge", "male", "Mexico · friendly"),
            ("es-MX-DaliaNeural", "Dalia", "female", "Mexico · bright"),
        ],
    },
    "French": {
        "sample": "Salut ! Voici la voix de ton prochain reel viral.",
        "voices": [
            ("fr-FR-RemyMultilingualNeural", "Rémy", "male", "natural, modern"),
            ("fr-FR-VivienneMultilingualNeural", "Vivienne", "female", "natural, warm"),
            ("fr-FR-HenriNeural", "Henri", "male", "classic"),
        ],
    },
    "German": {
        "sample": "Hallo! Das ist die Stimme deines nächsten viralen Reels.",
        "voices": [
            ("de-DE-FlorianMultilingualNeural", "Florian", "male", "natural, modern"),
            ("de-DE-SeraphinaMultilingualNeural", "Seraphina", "female", "natural, warm"),
            ("de-DE-ConradNeural", "Conrad", "male", "deep"),
        ],
    },
    "Portuguese": {
        "sample": "Olá! Esta é a voz do seu próximo reel viral.",
        "voices": [
            ("pt-BR-AntonioNeural", "Antônio", "male", "Brazil · friendly"),
            ("pt-BR-ThalitaMultilingualNeural", "Thalita", "female", "Brazil · natural"),
            ("pt-BR-FranciscaNeural", "Francisca", "female", "Brazil · bright"),
        ],
    },
    "Arabic": {
        "sample": "مرحبا! هذا صوت الفيديو القادم الذي سينتشر.",
        "voices": [
            ("ar-SA-HamedNeural", "Hamed", "male", "Saudi · warm"),
            ("ar-SA-ZariyahNeural", "Zariyah", "female", "Saudi · bright"),
            ("ar-AE-HamdanNeural", "Hamdan", "male", "UAE · confident"),
            ("ar-AE-FatimaNeural", "Fatima", "female", "UAE · soft"),
        ],
    },
}

# Languages written in Latin script get uppercase "creator" captions
LATIN_LANGUAGES = {"English", "Hinglish", "Spanish", "French", "German", "Portuguese"}

_ALL_IDS = {v[0] for lang in CATALOG.values() for v in lang["voices"]}


def catalog() -> List[Dict]:
    return [
        {
            "language": lang,
            "sample": data["sample"],
            "voices": [{"id": vid, "name": n, "gender": g, "vibe": vibe} for vid, n, g, vibe in data["voices"]],
        }
        for lang, data in CATALOG.items()
    ]


def is_valid_voice(voice_id: Optional[str]) -> bool:
    return bool(voice_id) and voice_id in _ALL_IDS


def default_voice(language: str, gender: str = "male") -> Optional[str]:
    data = CATALOG.get(language)
    if not data:
        return None
    for vid, _, g, _ in data["voices"]:
        if g == gender:
            return vid
    return data["voices"][0][0]


def sample_text(language: str) -> str:
    return (CATALOG.get(language) or CATALOG["English"])["sample"]


def language_of(voice_id: str) -> Optional[str]:
    for lang, data in CATALOG.items():
        if any(v[0] == voice_id for v in data["voices"]):
            return lang
    return None
