import logging

from aiogram import BaseMiddleware
from sqlalchemy import Column, BigInteger, String, ForeignKey, Text, Boolean, delete, Integer, DateTime
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.future import select
from sqlalchemy.sql import expression, func
from typing import Callable, Dict, Any

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(Integer, unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    password = Column(String(21), nullable=False)
    admin_id = Column(BigInteger, nullable=False)
    is_active = Column(Boolean, server_default=expression.true(), nullable=False)
    current_question_index = Column(Integer, default=0)
    session_type = Column(String(30), nullable=True)
    number = Column(String(10), nullable=True)
    date = Column(DateTime, default=func.now())

    agenda_items = relationship("AgendaItem", back_populates="session")
    participants = relationship("Participant", back_populates="session", cascade="all, delete-orphan")

class AgendaItem(Base):
    __tablename__ = "agenda_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    description = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)
    proposed = Column(String(50), nullable=True)
    manual = Column(String(255), nullable=True)

    session = relationship("Session", back_populates="agenda_items")
    votes = relationship("Vote", back_populates="agenda_item")

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agenda_item_id = Column(Integer, ForeignKey("agenda_items.id"), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    vote = Column(String(10), nullable=False)

    agenda_item = relationship("AgendaItem", back_populates="votes")

class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    name = Column(String(50), nullable=False)

    session = relationship("Session", back_populates="participants")

class YouthCouncilInfo(Base):
    __tablename__ = 'youth_council_info'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    name = Column(String(255), nullable=False)
    city = Column(String(50), nullable=False)
    region = Column(String(255), nullable=False)
    head = Column(String(50), nullable=False)
    secretary = Column(String(50), nullable=False)

class Name(Base):
    __tablename__ = 'names'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    name = Column(String(50), nullable=False)
    name_rv = Column(String(60), nullable=True)

class Logging(Base):
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    name = Column(String(100), nullable=False)


# Database Utility Functions
class Database:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def add_session(self, session_code, session_name, session_password, admin_id):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.admin_id == admin_id, Session.is_active.is_(True))
            )
            active_session = result.scalars().first()
            if active_session:
                active_session.is_active = False
                await session.commit()
                logging.warning(f"У адміністратора {admin_id} вже є активна сесія з кодом {active_session.code}. Завершуємо її.")

            new_session = Session(
                code=int(session_code),
                name=session_name,
                password=session_password,
                admin_id=admin_id
            )
            session.add(new_session)
            await session.commit()

    async def set_session_agenda(self, session_code, agenda):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.code == int(session_code))
            )
            session_obj = result.scalar_one_or_none()
            if session_obj:
                await session.execute(
                    delete(AgendaItem).where(AgendaItem.session_id == session_obj.id)
                )
                for position, description in enumerate(agenda, start=1):
                    new_item = AgendaItem(
                        session_id=session_obj.id,
                        description=description,
                        position=position
                    )
                    session.add(new_item)
                await session.commit()


    async def start_voting(self, session_code):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.code == int(session_code))
            )
            session_obj = result.scalar_one_or_none()
            if session_obj:
                session_obj.is_active = True
                await session.commit()

    async def end_session(self, session_code):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.code == int(session_code))
            )
            session_obj = result.scalar_one_or_none()

            if session_obj:
                session_obj.is_active = False
                results = {}

                agenda_result = await session.execute(
                    select(AgendaItem).where(AgendaItem.session_id == session_obj.id)
                )
                agenda_items = agenda_result.scalars().all()

                participants_result = await session.execute(
                    select(Participant).where(Participant.session_id == session_obj.id)
                )
                participants = participants_result.scalars().all()
                total_participants = len(participants)

                for item in agenda_items:
                    votes_result = await session.execute(
                        select(Vote).where(Vote.agenda_item_id == item.id)
                    )
                    votes = votes_result.scalars().all()

                    vote_counts = {"for": 0, "against": 0, "abstain": 0}
                    voted_users = set()

                    for vote in votes:
                        if vote.vote == "За":
                            vote_counts["for"] += 1
                        elif vote.vote == "Проти":
                            vote_counts["against"] += 1
                        elif vote.vote == "Утримаюсь":
                            vote_counts["abstain"] += 1
                        voted_users.add(vote.user_id)

                    not_voted = total_participants - len(voted_users)
                    vote_counts["not_voted"] = not_voted

                    results[item.description] = vote_counts

                await session.commit()
                return results

    async def get_admin_session(self, admin_id):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.admin_id == admin_id, Session.is_active.is_(True))
            )
            session_obj = result.scalars().first()
            if session_obj is None:
                logging.warning(f"Сесія для admin_id {admin_id} не знайдена")
            return session_obj.code if session_obj else None

    async def get_session_agenda(self, session_code):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.code == session_code)
            )
            session_obj = result.scalar_one_or_none()
            if session_obj:
                # Отримуємо відсортований порядок денний
                agenda_result = await session.execute(
                    select(AgendaItem)
                    .where(AgendaItem.session_id == session_obj.id)
                    .order_by(AgendaItem.position)
                )
                agenda_items = agenda_result.scalars().all()

                sorted_agenda = [item.description for item in agenda_items]
                return tuple(sorted_agenda)
            return []
    async def add_vote(self, session_code, user_id, question, vote):
        """
        Додає голос учасника до бази даних.
        :param session_code: Код сесії.
        :param user_id: ID користувача.
        :param question: Питання, за яке голосують.
        :param vote: Варіант голосу ("За", "Проти", "Утримаюсь").
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.code == int(session_code))
            )
            session_obj = result.scalar_one_or_none()
            if not session_obj:
                logging.warning(f"Сесія з кодом {session_code} не знайдена для голосування.")
                return

            agenda_result = await session.execute(
                select(AgendaItem).where(AgendaItem.session_id == session_obj.id, AgendaItem.description == question)
            )
            agenda_item = agenda_result.scalar_one_or_none()
            if not agenda_item:
                logging.warning(f"Питання '{question}' не знайдено в порядку денному сесії {session_code}.")
                return

            existing_vote_result = await session.execute(
                select(Vote).where(Vote.agenda_item_id == agenda_item.id, Vote.user_id == user_id)
            )
            existing_vote = existing_vote_result.scalar_one_or_none()
            if existing_vote:
                logging.info(f"Користувач {user_id} вже голосував за питання '{question}'. Оновлюємо голос.")
                existing_vote.vote = vote
            else:
                new_vote = Vote(
                    agenda_item_id=agenda_item.id,
                    user_id=user_id,
                    vote=vote
                )
                session.add(new_vote)

            await session.commit()
            logging.info(f"Голос користувача {user_id} за питання '{question}' успішно збережено.")

    async def check_all_votes_collected(self, session_code, question):
        async with self.session_factory() as session:
            session_obj = await session.execute(
                select(Session).where(Session.code == int(session_code))
            )
            session_obj = session_obj.scalar_one_or_none()
            if not session_obj:
                return False

            agenda_item_result = await session.execute(
                select(AgendaItem).where(AgendaItem.session_id == session_obj.id, AgendaItem.description == question)
            )
            agenda_item = agenda_item_result.scalar_one_or_none()
            if not agenda_item:
                return False

            participants_result = await session.execute(
                select(Participant).where(Participant.session_id == session_obj.id)
            )
            total_participants = len(participants_result.scalars().all())

            vote_count_result = await session.execute(
                select(Vote).where(Vote.agenda_item_id == agenda_item.id)
            )
            total_votes = len(vote_count_result.scalars().all())
            return total_votes >= total_participants

    async def count_of_participants(self, session_code):
        async with self.session_factory() as session:
            session_obj = await session.execute(
                select(Session).where(Session.code == int(session_code))
            )
            session_obj = session_obj.scalar_one_or_none()
            if not session_obj:
                return False

            participants_result = await session.execute(
                select(Participant).where(Participant.session_id == session_obj.id)
            )
            total_participants = len(participants_result.scalars().all())
            return total_participants

    async def get_vote_results(self, session_code, question):
        async with self.session_factory() as session:
            session_obj = await session.execute(
                select(Session).where(Session.code == int(session_code))
            )
            session_obj = session_obj.scalar_one_or_none()
            if not session_obj:
                return {}

            agenda_item_result = await session.execute(
                select(AgendaItem).where(AgendaItem.session_id == session_obj.id, AgendaItem.description == question)
            )
            agenda_item = agenda_item_result.scalar_one_or_none()
            if not agenda_item:
                return {}

            vote_result = await session.execute(
                select(Vote).where(Vote.agenda_item_id == agenda_item.id)
            )
            votes = vote_result.scalars().all()

            vote_counts = {"За": 0, "Проти": 0, "Утримаюсь": 0}
            for vote in votes:
                if vote.vote in vote_counts:
                    vote_counts[vote.vote] += 1

            return vote_counts

    async def add_participant(self, session_code, user_id, user_name):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.code == int(session_code))
            )
            session_obj = result.scalar_one_or_none()
            if not session_obj:
                logging.warning(f"Сесія з кодом {session_code} не знайдена.")
                return

            participant_result = await session.execute(
                select(Participant).where(
                    Participant.session_id == session_obj.id,
                    Participant.user_id == user_id
                )
            )
            participant = participant_result.scalar_one_or_none()
            if participant:
                logging.info(f"Користувач {user_id} вже є учасником сесії {session_code}.")
                return

            new_participant = Participant(
                session_id=session_obj.id,
                user_id=user_id,
                name=user_name
            )
            session.add(new_participant)
            await session.commit()
            logging.info(f"Користувач {user_id} доданий до сесії {session_code} як {user_name}.")

    async def get_session_participants(self, session_code):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Participant.user_id).join(Session).where(Session.code == int(session_code))
            )
            return [row[0] for row in result.fetchall()]  # Повертаємо лише user_id

    async def get_current_question_index(self, session_code):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session.current_question_index).where(Session.code == int(session_code))
            )
            return result.scalar_one_or_none()

    async def set_current_question_index(self, session_code, question_index):
        async with self.session_factory() as session:
            session_obj = await session.execute(
                select(Session).where(Session.code == int(session_code))
            )
            session_obj = session_obj.scalar_one_or_none()
            if session_obj:
                session_obj.current_question_index = question_index
                await session.commit()

    async def get_admin_id(self, session_code: int) -> int:
        """
        Отримати ID адміністратора за кодом сесії.
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session.admin_id).where(Session.code == int(session_code))
            )
            return result.scalar_one_or_none()

    async def has_user_voted(self, session_code, user_id, question):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Vote).where(
                    Vote.agenda_item_id == select(AgendaItem.id)
                    .where(
                        AgendaItem.description == question,
                        AgendaItem.session_id == select(Session.id)
                        .where(Session.code == int(session_code))
                        .scalar_subquery()
                    )
                    .scalar_subquery(),
                    Vote.user_id == user_id
                )
            )
            return result.scalar_one_or_none() is not None

    async def remove_participant(self, session_code: int, user_id: int):
        async with self.session_factory() as session:
            session_result = await session.execute(
                select(Session.id).where(Session.code == int(session_code))
            )
            session_id = session_result.scalar_one_or_none()
            if not session_id:
                raise Exception(f"Сесія з кодом {session_code} не знайдена.")

            await session.execute(
                delete(Participant).where(
                    Participant.session_id == session_id,
                    Participant.user_id == user_id
                )
            )
            await session.commit()

    async def get_all_vote_results(self, session_code: int) -> dict:
        """Отримує всі результати голосування по сесії."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session.id).where(Session.code == int(session_code))
            )
            session_id = result.scalar_one_or_none()

            if not session_id:
                raise ValueError("❌ Сесія з таким кодом не знайдена.")

            # Отримуємо всі питання порядку денного
            agenda_result = await session.execute(
                select(AgendaItem).where(AgendaItem.session_id == session_id)
            )
            agenda_items = agenda_result.scalars().all()

            # Отримуємо список учасників сесії
            participants_result = await session.execute(
                select(Participant.user_id).where(Participant.session_id == session_id)
            )
            participants = participants_result.scalars().all()
            total_participants = len(participants)

            voting_results = {}

            for item in agenda_items:
                # Отримуємо всі голоси по конкретному питанню
                votes_result = await session.execute(
                    select(Vote.user_id, Vote.vote).where(Vote.agenda_item_id == item.id)
                )
                votes = votes_result.fetchall()

                vote_counts = {"for": 0, "against": 0, "abstain": 0}
                voted_users = set()

                for user_id, vote in votes:
                    if vote == "За":
                        vote_counts["for"] += 1
                    elif vote == "Проти":
                        vote_counts["against"] += 1
                    elif vote == "Утримаюсь":
                        vote_counts["abstain"] += 1
                    voted_users.add(user_id)

                not_voted = total_participants - len(voted_users)
                vote_counts["not_voted"] = max(0, not_voted)  # Запобігає від'ємним значенням

                voting_results[item.description] = vote_counts

            return voting_results

    async def save_youth_council_info(self, user_id, name, city, region, head, secretary):
        async with self.session_factory() as session:
            existing_info = await session.execute(
                select(YouthCouncilInfo).where(YouthCouncilInfo.user_id == user_id)
            )
            existing_info = existing_info.scalar_one_or_none()

            if existing_info:
                existing_info.name = name
                existing_info.city = city
                existing_info.region = region
                existing_info.head = head
                existing_info.secretary = secretary
            else:
                new_info = YouthCouncilInfo(
                    user_id=user_id,
                    name=name,
                    city=city,
                    region=region,
                    head=head,
                    secretary=secretary
                )
                session.add(new_info)

            await session.commit()

    async def get_session_participants_with_names(self, session_code):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.code == int(session_code))
            )
            session_obj = result.scalar_one_or_none()
            if not session_obj:
                logging.warning(f"Сесія з кодом {session_code} не знайдена.")
                return []

            participants_result = await session.execute(
                select(Participant).where(Participant.session_id == session_obj.id)
            )
            participants = participants_result.scalars().all()
            return [{"id": p.user_id, "name": p.name} for p in participants]

    async def set_agenda_item_proposer(self, session_code, question, proposer_name):
        async with self.session_factory() as session:
            result = await session.execute(
                select(AgendaItem).where(AgendaItem.session_id == select(Session.id)
                                         .where(Session.code == int(session_code))
                                         .scalar_subquery(),
                                         AgendaItem.description == question)
            )
            agenda_item = result.scalar_one_or_none()

            if agenda_item:
                agenda_item.proposed = proposer_name
                await session.commit()


    async def get_full_youth_council_info(self, user_id):
        """Повертає всі дані Молодіжної ради користувача."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(
                    YouthCouncilInfo.name,
                    YouthCouncilInfo.city,
                    YouthCouncilInfo.region,
                    YouthCouncilInfo.head,
                    YouthCouncilInfo.secretary,
                ).where(YouthCouncilInfo.user_id == user_id)
            )
            council_info = result.first()
            if council_info:
                return {
                    "name": council_info.name,
                    "city": council_info.city,
                    "region": council_info.region,
                    "head": council_info.head,
                    "secretary": council_info.secretary,
                }
            return None

    async def get_proposed_names_by_admin(self, session_code, admin_id):
        async with self.session_factory() as session:
            result = await session.execute(
                select(AgendaItem.proposed)
                .where(AgendaItem.session_id == select(Session.id)
                       .where(Session.code == int(session_code))
                       .scalar_subquery())
            )
            return list(set(row[0] for row in result.fetchall() if row[0]))

    async def get_name_rv(self, user_id, name):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Name).where(Name.user_id == user_id, Name.name == name)
            )
            return result.scalar_one_or_none()

    async def update_name_rv(self, user_id, name, name_rv):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Name).where(Name.user_id == user_id, Name.name == name)
            )
            name_entry = result.scalar_one_or_none()

            if name_entry:
                name_entry.name_rv = name_rv
            else:
                new_name_entry = Name(user_id=user_id, name=name, name_rv=name_rv)
                session.add(new_name_entry)

            await session.commit()

    async def get_proposed_name(self, session_code, question):
        """
        Отримує ім'я особи, яка запропонувала питання (proposed), для заданого питання.

        :param session_code: Код сесії.
        :param question: Текст питання.
        :return: Ім'я особи, яка запропонувала питання, або None.
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(AgendaItem.proposed)
                .where(
                    AgendaItem.session_id == select(Session.id)
                    .where(Session.code == int(session_code))
                    .scalar_subquery(),
                    AgendaItem.description == question
                )
            )
            return result.scalar_one_or_none()

    async def update_session_details(self, session_code, protocol_number, session_type):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.code == int(session_code))
            )
            session_obj = result.scalar_one_or_none()
            if session_obj:
                session_obj.number = protocol_number
                session_obj.session_type = session_type
                await session.commit()

    async def get_session_details(self, session_code):
        """Повертає тип засідання та номер протоколу."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session.session_type, Session.number)
                .where(Session.code == int(session_code))
            )
            session_details = result.first()
            if session_details:
                return {
                    "session_type": session_details.session_type or "Не вказано",
                    "number": session_details.number or "Не вказано"
                }
            return {"session_type": "Не вказано", "number": "Не вказано"}

    async def delete_session(self, session_code: int):
        """Видаляє сесію за її кодом"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.code == session_code)
            )
            session_obj = result.scalar_one_or_none()

            if session_obj:
                await session.delete(session_obj)
                await session.commit()
                logging.info(f"Сесія {session_code} успішно видалена.")

    async def get_last_sessions(self, limit: int = 10):
        """Отримує останні N сесій."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).order_by(Session.date.desc()).limit(limit)
            )
            return result.scalars().all()

    async def get_session_by_code(self, session_code):
        """Отримує сесію за її кодом, уникаючи проблеми з типами."""
        async with self.session_factory() as session:
            try:
                session_code = int(session_code)  # Приведення до int
            except ValueError:
                return None  # Якщо не вдалося перетворити, повертаємо None

            result = await session.execute(
                select(Session).where(Session.code == session_code)
            )
            return result.scalar_one_or_none()

    ### --- AGENDA ITEMS FUNCTIONS --- ###
    async def get_agenda_items(self, session_id: int):
        """Отримує всі пункти порядку денного для сесії."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(AgendaItem).where(AgendaItem.session_id == session_id)
            )
            return result.scalars().all()

    async def delete_agenda_items(self, session_id: int):
        """Видаляє всі пункти порядку денного для сесії."""
        async with self.session_factory() as session:
            await session.execute(
                delete(AgendaItem).where(AgendaItem.session_id == session_id)
            )
            await session.commit()

    ### --- VOTE FUNCTIONS --- ###
    async def get_votes_for_session(self, session_id: int):
        """Отримує всі голоси для сесії."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Vote).where(Vote.agenda_item_id == session_id)
            )
            return result.scalars().all()

    async def delete_votes_for_session(self, session_id: int):
        """Видаляє всі голоси для сесії."""
        async with self.session_factory() as session:
            await session.execute(
                delete(Vote).where(Vote.agenda_item_id == session_id)
            )
            await session.commit()

    ### --- PARTICIPANT FUNCTIONS --- ###
    async def get_participants_for_session(self, session_id: int):
        """Отримує всіх учасників сесії."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Participant).where(Participant.session_id == session_id)
            )
            return result.scalars().all()

    async def get_participant_count(self, session_id: int):
        """Отримує кількість учасників сесії."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(func.count()).where(Participant.session_id == session_id)
            )
            return result.scalar()

    async def delete_participants_for_session(self, session_id: int):
        """Видаляє всіх учасників сесії."""
        async with self.session_factory() as session:
            await session.execute(
                delete(Participant).where(Participant.session_id == session_id)
            )
            await session.commit()

    ### --- YOUTH COUNCIL INFO FUNCTIONS --- ###
    async def get_youth_council_info(self, admin_id: int):
        """Отримує інформацію про Молодіжну раду за ID адміна."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(YouthCouncilInfo).where(YouthCouncilInfo.user_id == admin_id)
            )
            return result.scalar_one_or_none()

    ### --- USER STATISTICS FUNCTIONS --- ###
    async def get_user_statistics(self, user_id: int):
        """Отримує статистику користувача, якщо він існує, з найчастішим іменем та топ-3 молодіжними радами."""
        async with self.session_factory() as session:
            # Перевіряємо, чи користувач існує в БД
            user_exists = await session.execute(
                select(Participant.user_id).where(Participant.user_id == user_id)
            )
            if not user_exists.fetchone():
                return None  # Користувача немає в базі

            # Отримуємо ім'я, яке найчастіше зустрічається у таблиці `participants`
            most_common_name_query = await session.execute(
                select(Participant.name, func.count(Participant.name))
                .where(Participant.user_id == user_id)
                .group_by(Participant.name)
                .order_by(func.count(Participant.name).desc())  # Сортуємо за частотою
                .limit(1)
            )
            most_common_name_result = most_common_name_query.fetchone()
            user_name = most_common_name_result[0] if most_common_name_result else "Невідомий"

            # Отримуємо кількість сесій, у яких користувач брав участь
            participation_count_query = await session.execute(
                select(func.count()).where(Participant.user_id == user_id)
            )
            participation_count = participation_count_query.scalar()

            # Отримуємо кількість разів, коли користувач був адміном
            admin_count_query = await session.execute(
                select(func.count()).where(Session.admin_id == user_id)
            )
            admin_count = admin_count_query.scalar()

            # Отримуємо топ-3 молодіжні ради, в яких користувач найчастіше виступав
            youth_council_query = await session.execute(
                select(YouthCouncilInfo.name, func.count(YouthCouncilInfo.name))
                .join(Session, YouthCouncilInfo.user_id == Session.admin_id)  # Приєднуємо до сесій
                .join(Participant, Session.id == Participant.session_id)  # Приєднуємо учасників
                .where(Participant.user_id == user_id)
                .group_by(YouthCouncilInfo.name)
                .order_by(func.count(YouthCouncilInfo.name).desc())  # Сортуємо за кількістю
                .limit(3)
            )
            youth_councils = youth_council_query.fetchall()

            # Формуємо список топ-3 молодіжних рад
            top_youth_councils = "\n".join(
                [f"{index + 1}. {council[0]} ({council[1]} разів)" for index, council in enumerate(youth_councils)]
            ) if youth_councils else "Немає даних"

            return {
                "user_id": user_id,
                "name": user_name,
                "participation_count": participation_count,
                "admin_count": admin_count,
                "top_youth_councils": top_youth_councils
            }

    async def get_all_users(self, limit: int = 30):
        """Отримує список всіх користувачів (обмежено 30), використовуючи найчастіше зустрічаючеся ім'я."""
        async with self.session_factory() as session:
            # Отримуємо користувачів разом із найчастішим іменем
            result = await session.execute(
                select(
                    Participant.user_id,
                    Participant.name,
                    func.count(Participant.name)
                )
                .group_by(Participant.user_id, Participant.name)
                .order_by(Participant.user_id, func.count(Participant.name).desc())
                # Сортуємо по user_id і найбільшому count
            )

            # Обробляємо дані, щоб залишити лише найчастіше ім'я для кожного user_id
            user_data = {}
            for user_id, name, count in result.fetchall():
                if user_id not in user_data:  # Додаємо перший запис, бо він уже відсортований по найбільшій кількості
                    user_data[user_id] = name

            # Конвертуємо в список (обмежуємо `limit`)
            users_list = list(user_data.items())[:limit]

            return users_list

    ### --- FULL SESSION CLEANUP FUNCTION --- ###
    async def delete_related_data(self, session_code: int):
        """Видаляє всі пов'язані з сесією дані (порядок денний, голоси, учасників)."""
        async with self.session_factory() as session:
            # Отримуємо сесію
            result = await session.execute(
                select(Session).where(Session.code == session_code)
            )
            session_obj = result.scalar_one_or_none()

            if session_obj:
                # Видаляємо всі пов'язані записи
                await session.execute(
                    delete(AgendaItem).where(AgendaItem.session_id == session_obj.id)
                )
                await session.execute(
                    delete(Vote).where(Vote.agenda_item_id == session_obj.id)
                )
                await session.execute(
                    delete(Participant).where(Participant.session_id == session_obj.id)
                )

                await session.commit()
                logging.info(f"Всі пов'язані дані для сесії {session_code} видалені.")

    async def get_admin_name(self, admin_id: int):
        """Отримує ім'я адміна, яке найчастіше зустрічається серед учасників його сесій."""
        async with self.session_factory() as session:
            # Перевіряємо, чи адмін є учасником хоча б однієї сесії
            admin_exists = await session.execute(
                select(Participant.user_id).where(Participant.user_id == admin_id).limit(1)
                # Запобігає MultipleResultsFound
            )
            if not admin_exists.scalar_one_or_none():
                return "Невідомий адмін"

            # Отримуємо ім'я, яке найчастіше зустрічається у таблиці `participants`
            most_common_name_query = await session.execute(
                select(Participant.name, func.count(Participant.name))
                .where(Participant.user_id == admin_id)
                .group_by(Participant.name)
                .order_by(func.count(Participant.name).desc())  # Сортуємо за частотою
                .limit(1)
            )
            most_common_name_result = most_common_name_query.fetchone()

            return most_common_name_result[0] if most_common_name_result else "Невідомий адмін"

    async def get_questions_count(self, session_id: int):
        """Підраховує кількість питань у сесії"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(func.count()).where(AgendaItem.session_id == session_id)
            )
            return result.scalar() or 0

    async def check_session(self, session_code: int):
        """Перевіряє, чи існує сесія і чи вона активна."""
        async with self.session_factory() as session:
            try:
                session_code = int(session_code)  # Приведення до int (щоб уникнути помилок)
            except ValueError:
                return None  # Якщо код некоректний

            result = await session.execute(
                select(Session)
                .where(Session.code == session_code)
                .where(Session.is_active == True)  # Перевіряємо, що сесія активна
            )
            session_obj = result.scalar_one_or_none()

            return session_obj  # Повертаємо сесію або None, якщо її нема / не активна

    async def close_session(self, session_code: int):
        """Закриває сесію (ставить is_active = False)."""
        async with self.session_factory() as session:
            try:
                session_code = int(session_code)  # Перетворюємо у число (щоб уникнути помилок)
            except ValueError:
                return None  # Якщо код некоректний

            # Отримуємо сесію
            result = await session.execute(
                select(Session).where(Session.code == session_code)
            )
            session_obj = result.scalar_one_or_none()

            if not session_obj:
                return None  # Сесія не знайдена

            if not session_obj.is_active:
                return "Сесія вже закрита!"  # Якщо сесія вже неактивна

            # Закриваємо сесію
            session_obj.is_active = False
            await session.commit()


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db

    async def __call__(self, handler: Callable, event: Any, data: Dict[str, Any]) -> Any:
        data['db'] = self.db
        return await handler(event, data)
