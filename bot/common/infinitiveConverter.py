import spacy
import pymorphy2

# Завантажуємо українську NLP-модель
nlp = spacy.load("uk_core_news_sm")

# Ініціалізуємо морфологічний аналізатор для корекції відмінків
morph = pymorphy2.MorphAnalyzer(lang="uk")

# Словник відповідностей (іменник → інфінітив)
conversion_dict = {
    "відкриття": "відкрити",
    "запуск": "запустити",
    "створення": "створити",
    "завершення": "завершити",
    "розгляд": "розглянути",
    "припинення": "припинити",
    "оголошення": "оголосити",
    "затвердження": "затвердити",
    "обрання": "обрати",
    "цифровізація": "цифровізувати",
    "цифровізацію": "цифровізувати"
}


def correct_case(word, target_case="nomn"):
    """
    Виправляє відмінок слова на потрібний (наприклад, називний - "nomn").
    """
    parsed = morph.parse(word)
    for p in parsed:
        if target_case in p.tag:
            return p.normal_form  # Якщо слово вже в потрібному відмінку, повертаємо його
    return parsed[0].inflect({target_case}).word if parsed[0].inflect({target_case}) else word


def convert_to_infinitive(sentence):
    """Перетворює речення у форму інфінітива та виправляє відмінки."""
    doc = nlp(sentence)

    # Видаляємо "Про" на початку речення
    words = sentence.split()
    if words[0].lower() == "про":
        sentence = " ".join(words[1:])  # Видаляємо "Про"

    new_sentence = sentence

    # Аналізуємо речення
    for token in doc:
        if token.pos_ == "NOUN" and token.text.lower() in conversion_dict:
            infinitive = conversion_dict[token.text.lower()]
            new_sentence = new_sentence.replace(token.text, infinitive, 1)  # Замінюємо лише перше входження

            # Виправляємо наступне слово (прикметник або іменник у неправильному відмінку)
            words = new_sentence.split()
            idx = words.index(infinitive) + 1  # Наступне слово
            if idx < len(words):
                next_word = words[idx]
                corrected_word = correct_case(next_word, "nomn")  # Перетворюємо у називний відмінок
                words[idx] = corrected_word  # Замінюємо
                new_sentence = " ".join(words)  # Збираємо назад

            break  # Виправили перше знайдене слово, далі не потрібно

    return new_sentence


def capitalize_first_word(sentence):
    """Робить перше слово в реченні з великої літери, решту не змінює."""
    if not sentence:
        return sentence  # Якщо рядок пустий, повертаємо його

    words = sentence.split(" ", 1)  # Розділяємо речення на перше слово та решту
    first_word = words[0].capitalize()  # Робимо перше слово з великої літери
    rest_of_sentence = words[1] if len(words) > 1 else ""  # Решта речення

    return first_word + (" " + rest_of_sentence if rest_of_sentence else "")