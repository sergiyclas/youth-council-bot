import logging

from aiogram import BaseMiddleware, types
from sqlalchemy import Column, BigInteger, String, ForeignKey, Text, Boolean, delete, func, Integer
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.future import select
from sqlalchemy.sql import expression
from typing import Callable, Dict, Any

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    admin_id = Column(BigInteger, nullable=False)
    is_active = Column(Boolean, server_default=expression.true(), nullable=False)
    current_question_index = Column(Integer, default=0)

    agenda_items = relationship("AgendaItem", back_populates="session")
    participants = relationship("Participant", back_populates="session", cascade="all, delete-orphan")

class AgendaItem(Base):
    __tablename__ = "agenda_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("sessions.id"), nullable=False)
    description = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)

    session = relationship("Session", back_populates="agenda_items")
    votes = relationship("Vote", back_populates="agenda_item")

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agenda_item_id = Column(Integer, ForeignKey("agenda_items.id"), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    vote = Column(String(10), nullable=False)  # "За", "Проти", "Утримаюсь"

    agenda_item = relationship("AgendaItem", back_populates="votes")

class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    name = Column(String(255), nullable=False)

    session = relationship("Session", back_populates="participants")

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
                code=session_code,
                name=session_name,
                password=session_password,
                admin_id=admin_id
            )
            session.add(new_session)
            await session.commit()

    async def set_session_agenda(self, session_code, agenda):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.code == session_code)
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
                select(Session).where(Session.code == str(session_code))
            )
            session_obj = result.scalar_one_or_none()
            if session_obj:
                session_obj.is_active = True
                await session.commit()

    async def end_session(self, session_code):
        async with self.session_factory() as session:
            result = await session.execute(
                select(Session).where(Session.code == str(session_code))
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
                select(Session).where(Session.code == str(session_code))
            )
            session_obj = result.scalar_one_or_none()
            if session_obj:
                agenda_result = await session.execute(
                    select(AgendaItem).where(AgendaItem.session_id == session_obj.id)
                )
                agenda_items = agenda_result.scalars().all()
                return [item.description for item in agenda_items]
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
                select(Session).where(Session.code == str(session_code))
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
                select(Session).where(Session.code == str(session_code))
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
                select(Session).where(Session.code == str(session_code))
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
                select(Session).where(Session.code == str(session_code))
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
                select(Session).where(Session.code == str(session_code))
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
                    select(Participant.user_id).join(Session).where(Session.code == str(session_code))
                )
                return [row[0] for row in result.fetchall()]  # Повертаємо лише user_id

        async def get_session_by_code(self, session_code):
            async with self.session_factory() as session:
                result = await session.execute(
                    select(Session).where(Session.code == str(session_code))
                )
                return result.scalar_one_or_none()

        async def get_current_question_index(self, session_code):
            async with self.session_factory() as session:
                result = await session.execute(
                    select(Session.current_question_index).where(Session.code == str(session_code))
                )
                return result.scalar_one_or_none()

        async def set_current_question_index(self, session_code, question_index):
            async with self.session_factory() as session:
                session_obj = await session.execute(
                    select(Session).where(Session.code == str(session_code))
                )
                session_obj = session_obj.scalar_one_or_none()
                if session_obj:
                    session_obj.current_question_index = question_index
                    await session.commit()

        async def get_admin_id(self, session_code: str) -> int:
            """
            Отримати ID адміністратора за кодом сесії.
            """
            async with self.session_factory() as session:
                result = await session.execute(
                    select(Session.admin_id).where(Session.code == str(session_code))
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
                            .where(Session.code == str(session_code))
                            .scalar_subquery()
                        )
                        .scalar_subquery(),
                        Vote.user_id == user_id
                    )
                )
                return result.scalar_one_or_none() is not None

        async def remove_participant(self, session_code: str, user_id: int):
            async with self.session_factory() as session:
                session_result = await session.execute(
                    select(Session.id).where(Session.code == str(session_code))
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

        async def get_all_vote_results(self, session_code: str) -> dict:
            async with self.session_factory() as session:
                result = await session.execute(
                    select(Session.id).where(Session.code == str(session_code))
                )
                session_id = result.scalar_one_or_none()
                if not session_id:
                    raise ValueError("Сесія з таким кодом не знайдена.")

                agenda_result = await session.execute(
                    select(AgendaItem.id, AgendaItem.description).where(AgendaItem.session_id == session_id)
                )
                agenda_items = agenda_result.all()

                voting_results = {}
                for agenda_item_id, description in agenda_items:
                    votes_result = await session.execute(
                        select(Vote.vote, func.count(Vote.id))
                        .where(Vote.agenda_item_id == agenda_item_id)
                        .group_by(Vote.vote)
                    )
                    votes = votes_result.all()

                    results = {"for": 0, "against": 0, "abstain": 0}
                    for vote, count in votes:
                        if vote == "За":
                            results["for"] = count
                        elif vote == "Проти":
                            results["against"] = count
                        elif vote == "Утримаюсь":
                            results["abstain"] = count

                    voting_results[description] = results

                return voting_results

        async def get_session_participants_with_names(self, session_code):
            async with self.session_factory() as session:
                result = await session.execute(
                    select(Session).where(Session.code == str(session_code))
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


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db

    async def __call__(self, handler: Callable, event: Any, data: Dict[str, Any]) -> Any:
        data['db'] = self.db
        return await handler(event, data)
