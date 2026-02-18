import re


def extract_emotion(input_text):
    pattern = r"^\((.*?)\)\s*(.*)"
    match = re.match(pattern, input_text)
    if match:
        return match.group(1), match.group(2)
    return "", input_text


test_cases = [
    ("(Happy) Hello world", ("Happy", "Hello world")),
    ("(Sad)I am sad", ("Sad", "I am sad")),
    ("Just text", ("", "Just text")),
    ("(Complex Emotion)   Text with spaces", ("Complex Emotion", "Text with spaces")),
    ("(Tag) (Another tag) Text", ("Tag", "(Another tag) Text")),
]


def run_tests():
    all_passed = True
    for input_text, expected in test_cases:
        result = extract_emotion(input_text)
        if result == expected:
            print(f"PASS: '{input_text}' -> {result}")
        else:
            print(f"FAIL: '{input_text}' -> Expected {expected}, got {result}")
            all_passed = False

    if all_passed:
        print("\nALL TESTS PASSED")
    else:
        print("\nSOME TESTS FAILED")
        exit(1)


if __name__ == "__main__":
    run_tests()
