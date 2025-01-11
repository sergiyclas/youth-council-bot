from docx import Document
from docx.enum.section import WD_ORIENTATION
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Cm
import os
from datetime import datetime
from bot.common.mini_libs import months_uk, questions

def set_page_margins(document):
    """
    Налаштовує поля документа згідно з вимогами.
    Верхнє: 1,59 см
    Нижнє: 1,88 см
    Ліве: 2,5 см
    Праве: 1,5 см
    """
    section = document.sections[0]
    section.page_height = Cm(29.7)  # Висота для аркуша А4
    section.page_width = Cm(21.0)  # Ширина для аркуша А4
    section.orientation = WD_ORIENTATION.PORTRAIT

    # Поля
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)


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
    participants = await db.get_session_participants_with_names(session_code)
    agenda = await db.get_session_agenda(session_code)
    voting_results = await db.get_all_vote_results(session_code)

    # Формуємо ім'я файлу протоколу
    date = datetime.now().strftime("%d_%m_%Y")
    file_name = f"{date}_Протокол_{session_code}.docx"
    file_path = os.path.join("protocols", file_name)

    # Створюємо документ
    document = Document()
    set_page_margins(document)

    # Встановлюємо загальний стиль шрифту
    style = document.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(14)

    # Заголовок протоколу
    title = document.add_paragraph()
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    title_run = title.add_run(f"Протокол № {session_name}\nПозачергового засідання Молодіжної ради при Рава-Руській міській раді")
    title_run.bold = True
    title_run.font.size = Pt(14)

    current_date = datetime.now()
    date_for_title = f"{current_date.day} {months_uk[current_date.month]} {current_date.year}"

    city = "м. Рава-Руська"
    font_size = 14
    max_width = 99

    text_with_spaces = f"{city}{' ' * (max_width - len(date_for_title) - 4)}{date_for_title} р."

    # Додаємо текст до документа
    paragraph = document.add_paragraph()
    run = paragraph.add_run(text_with_spaces)
    run.font.size = Pt(font_size)
    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    # Присутні
    present_paragraph = document.add_paragraph()
    present_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    present_paragraph.add_run(f"Присутні: {len(participants)} (додаток 1)").bold = True

    invited_paragraph = document.add_paragraph()
    invited_paragraph.add_run("Запрошені: ").bold = True
    invited_paragraph.add_run("-")

    # Порядок денний
    agenda_paragraph = document.add_paragraph()
    agenda_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    agenda_paragraph.add_run("Порядок денний:").bold = True

    for i, item in enumerate(agenda, start=1):
        document.add_paragraph(f"{item}", style='List Number')

    # Результати голосувань
    for i, (question, results) in enumerate(voting_results.items(), start=1):
        # Додаємо жирний текст для пункту "По {questions[i]} питанню слухали"
        paragraph = document.add_paragraph(style='Normal')
        run = paragraph.add_run(f"{i}. По {questions[i]} питанню слухали")
        run.bold = True

        document.add_paragraph(
            f"Дзеня Сергія, який запропонував {question.lower()}", style='Normal'
        )

        # Додаємо жирний текст для результатів голосування
        paragraph = document.add_paragraph(style='Normal')
        run = paragraph.add_run(
            f"Проголосували: \"ЗА\" - {results['for']}, \"ПРОТИ\" - {results['against']}, \"УТРИМАЛИСЬ\" - {results['abstain']}"
        )
        run.bold = True

        paragraph = document.add_paragraph(style='Normal')
        run = paragraph.add_run(f"Ухвалили:")
        run.bold = True

        paragraph = document.add_paragraph(style='Normal')
        run = paragraph.add_run(f"{question}")

    paragraph = document.add_paragraph(style='Normal')
    run = paragraph.add_run(f"{len(voting_results.items()) + 1}. Питання різне - не піднімалося")
    run.bold = True

    # Додаємо порожній абзац перед підписами для відступу
    document.add_paragraph("\n")

    # Головуючий засідання
    paragraph = document.add_paragraph(style='Normal')
    run = paragraph.add_run("Головуючий засідання: ")
    run.bold = True
    run = paragraph.add_run("Дзень Сергій _______________")

    # Додати відступ
    document.add_paragraph("\n\n")

    # Секретар засідання
    paragraph = document.add_paragraph(style='Normal')
    run = paragraph.add_run("Секретар засідання: ")
    run.bold = True
    run = paragraph.add_run("Близнак Марта ______________")

    # Зберігаємо файл
    os.makedirs("protocols", exist_ok=True)
    document.save(file_path)

    return file_path


async def generate_attendance_list_full(session_code, session_name, db):
    """
    Генерує анкету присутності для сесії.

    :param session_code: Код сесії.
    :param session_name: Назва сесії.
    :param db: Об'єкт бази даних.
    :return: Шлях до збереженого файлу анкети.
    """
    # Отримуємо учасників
    participants = await db.get_session_participants_with_names(session_code)

    # Формуємо ім'я файлу додатка
    date = datetime.now().strftime("%d_%m_%Y")
    file_name = f"{date}_Додаток_присутності_{session_code}.docx"
    file_path = os.path.join("protocols", file_name)

    # Створюємо документ
    document = Document()
    set_page_margins(document)

    # Додаток 1
    appendix = document.add_paragraph()
    appendix.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    appendix_run = appendix.add_run("Додаток 1")
    appendix_run.font.name = "Times New Roman"
    appendix_run.font.size = Pt(14)
    appendix_run.bold = True

    # Заголовок
    title = document.add_paragraph()
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    current_date = datetime.now()
    date_for_title = f"{current_date.day} {months_uk[current_date.month]} {current_date.year}"

    title_run = title.add_run(
        f"Реєстраційна анкета на засідання №{session_name}, {date_for_title} року\n"
        f"Молодіжної ради при Рава-Руській міській раді Львівського району Львівської області"
    )
    title_run.font.name = "Times New Roman"
    title_run.font.size = Pt(14)
    title_run.bold = False

    # Таблиця присутності
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"

    # Заголовки таблиці
    header_cells = table.rows[0].cells
    header_cells[0].text = "№ п/п"
    header_cells[1].text = "Прізвище, ім'я"
    header_cells[2].text = "Присутність"

    # Форматування заголовків таблиці
    for header_cell in header_cells:
        for paragraph in header_cell.paragraphs:
            for run in paragraph.runs:
                run.font.name = "Times New Roman"
                run.font.size = Pt(14)
                run.bold = True

    # Заповнення таблиці
    for index, participant in enumerate(participants, start=1):
        row_cells = table.add_row().cells
        row_cells[0].text = str(index)
        row_cells[1].text = participant["name"]
        row_cells[2].text = "+"

        for cell in row_cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(14)

    # Зберігаємо файл
    os.makedirs("attendance", exist_ok=True)
    document.save(file_path)

    return file_path