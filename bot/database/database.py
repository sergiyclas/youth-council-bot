class Database:
    def __init__(self):
        self.sessions = {}

    def create_session(self, code, name, password, admin_id):
        self.sessions[code] = {
            "name": name,
            "password": password,
            "admin_id": admin_id,
            "agenda": [],
            "participants": {},
            "votes": {},
            "current_question": 0
        }

    def get_session(self, code):
        return self.sessions.get(code)

    def get_session_by_admin(self, admin_id):
        for session in self.sessions.values():
            if session["admin_id"] == admin_id:
                return session
        return None

    def add_participant(self, code, user_id, name):
        if code in self.sessions:
            self.sessions[code]["participants"][user_id] = name

    def update_agenda(self, code, agenda):
        if code in self.sessions:
            self.sessions[code]["agenda"] = agenda

    def save_vote(self, code, question, user_id, vote):
        if code in self.sessions:
            self.sessions[code]["votes"].setdefault(question, []).append({user_id: vote})

    def all_votes_received(self, code, question):
        if code in self.sessions:
            participants = self.sessions[code]["participants"]
            votes = self.sessions[code]["votes"].get(question, [])
            voted_users = {list(vote.keys())[0] for vote in votes}
            return len(voted_users) == len(participants)

    def get_results_for_question(self, code, question):
        if code in self.sessions:
            votes = self.sessions[code]["votes"].get(question, [])
            results = {"За": 0, "Проти": 0, "Утримався": 0}
            for vote in votes:
                for _, v in vote.items():
                    results[v] += 1
            return results

    def get_results(self, code):
        if code in self.sessions:
            agenda = self.sessions[code]["agenda"]
            results = {}
            for question in agenda:
                results[question] = self.get_results_for_question(code, question)
            return results

    def delete_session(self, code):
        if code in self.sessions:
            del self.sessions[code]
