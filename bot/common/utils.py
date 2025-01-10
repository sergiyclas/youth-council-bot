from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import os
from datetime import datetime


async def generate_protocol(session_code, db):
    """
    Генерує протокол для завершеної сесії.

    :param session_code: Код сесії.
    :param db: Об'єкт бази даних.
    :return: Шлях до збереженого файлу протоколу.
    """
    # Отримуємо дані про сесію
    session = await db.get_session_by_code(session_code)
    if not session:
        raise ValueError("Сесія не знайдена.")

    session_name = session.name
    admin_id = session.admin_id
    # participants = await db.get_session_participants_with_status(session_code)  # Додайте статус присутності
    agenda = await db.get_session_agenda(session_code)
    voting_results = await db.get_all_vote_results(session_code)

    # Формуємо ім'я файлу протоколу
    date = datetime.now().strftime("%d_%m_%Y")
    file_name = f"Протокол_{session_code}_{date}.docx"
    file_path = os.path.join("protocols", file_name)

    # Створюємо документ
    document = Document()

    # Заголовок протоколу
    title = document.add_paragraph()
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    title_run = title.add_run(f"Протокол № {session_code}\nЗасідання Молодіжної ради \"{session_name}\"")
    title_run.bold = True
    title_run.font.size = Pt(14)

    # Дата і місце проведення
    date_and_location = document.add_paragraph()
    date_and_location.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    date_and_location.add_run(f"Онлайн через Telegram-бот\n{datetime.now().strftime('%d.%m.%Y')}").font.size = Pt(12)

    # Присутні
    document.add_paragraph("Присутні:", style='Normal').bold = True
    # for i, participant in enumerate(participants, start=1):
    #     name = participant.get("name", f"Користувач {participant['id']}")
    #     status = participant.get("status", "unknown")
    #     participant_status = "\u2705 Присутній" if status == "present" else "\u274C Відсутній"
    #     document.add_paragraph(f"{i}. {name} — {participant_status}", style='Normal')

    # Порядок денний
    document.add_paragraph("Порядок денний:", style='Normal').bold = True
    for i, item in enumerate(agenda, start=1):
        document.add_paragraph(f"{i}. {item}", style='List Number')

    # Результати голосувань
    document.add_paragraph("Результати голосувань:", style='Normal').bold = True
    for i, (question, results) in enumerate(voting_results.items(), start=1):
        if not isinstance(results, dict):
            raise ValueError(f"Некоректний формат результатів для питання '{question}'. Очікується словник.")
        document.add_paragraph(f"{i}. {question}", style='Normal').bold = True
        document.add_paragraph(
            f"За: {results.get('for', 0)}\nПроти: {results.get('against', 0)}\nУтримались: {results.get('abstain', 0)}",
            style='Normal'
        )

    # Зберігаємо файл
    os.makedirs("protocols", exist_ok=True)
    document.save(file_path)

    return file_path
