MORSE_CODE_DICT = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..', '1': '.----', '2': '..---', '3': '...--',
    '4': '....-', '5': '.....', '6': '-....', '7': '--...', '8': '---..',
    '9': '----.', '0': '-----', ' ': ' '
}

REVERSE_MORSE_DICT = {v: k for k, v in MORSE_CODE_DICT.items()}

def translate_morse(morse_code: str) -> str:
    """
    Translates a Morse code sequence (e.g., '.-') into a character.
    If multiple characters are given separated by spaces, they are translated individually.
    """
    words = morse_code.strip().split('   ') # 3 spaces for word separation
    translated_words = []
    
    for word in words:
        chars = word.split(' ')
        translated_chars = [REVERSE_MORSE_DICT.get(char, '?') for char in chars]
        translated_words.append(''.join(translated_chars))
        
    return ' '.join(translated_words)

def get_char_from_sequence(sequence: str) -> str:
    """
    Translates a single sequence of dots/dashes into a single character.
    """
    return REVERSE_MORSE_DICT.get(sequence, '?')
