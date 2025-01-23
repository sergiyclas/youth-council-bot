import spacy

# Завантажуємо українську NLP-модель
nlp = spacy.load("uk_core_news_sm")

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

# Простий словник корекції відмінків (лише найпоширеніші випадки)
case_correction = {
    "питання": "питання",
    "рішення": "рішення",
    "програму": "програма",
    "програмі": "програма",
    "діяльності": "діяльність",
    "розвитку": "розвиток",
    "затвердження": "затвердити",
    "завершення": "завершити",
}


def correct_case_manual(word, target_case="nomn"):
    """
    Простий метод виправлення відмінків без використання pymorphy2.
    Просто замінює слова, якщо вони є в нашому словнику.
    """
    return case_correction.get(word.lower(), word)


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
                corrected_word = correct_case_manual(next_word, "nomn")  # Перетворюємо у називний відмінок
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
