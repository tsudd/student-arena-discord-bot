from .recorder_config import *
from ..dataprovider.back_config import NAME_ACCESSOR
import logging
import random
import datetime
from .player import Player
from .question import Question

from ..config import *


class Quiz(object):
    def __init__(self, cid, initiator, players: list, topic: list, questions: list, time_to_ans=10):
        self.players = {}
        self.cid = cid
        self.initiator = initiator
        self.state = State()
        self.topic = topic
        self.answer_time = time_to_ans
        self.rounds_amount = len(questions)
        self.question_message = None
        self.questions = []

        for player in players:
            self.players[player.id] = Player(
                player.id, player.nick if player.nick else player.name)

        for question in questions:
            self.questions.append(Question(question))

        self.question_stack = [*self.questions]
        self.state.player_counter = len(self.players)
        self.state.question_amount = len(self.questions)

        logging.info(
            f"Game in {self.cid} with {self.state.question_amount} questions was created.")

    def check_answers_and_kill(self, player_answers: dict, question: Question):
        kill_uid_list = []
        for playerid, answer in player_answers.items():
            if not question.check_answer(answer):
                self.players[playerid].kill()
                self.players[playerid].bad_question = self.state.last_question
                logging.info(f"{self.players[playerid].name} was killed!")
                self.state.dead_players.append(self.players[playerid])
                kill_uid_list.append(playerid)
            else:
                logging.info(
                    f"{self.players[playerid].name} got points after write answer!")
                self.players[playerid].add_points()
        self.state.last_ban_amount = len(kill_uid_list)
        self.state.dead_counter += self.state.last_ban_amount
        self.state.player_counter -= self.state.last_ban_amount
        self.state.question_answered += 1
        return kill_uid_list

    def get_question(self):
        if len(self.question_stack) == 0:
            return "No question."
        q = self.question_stack.pop()

        logging.info(f"New question was sent to players - {q.question_string}")
        self.state.last_question = q

        return q.get_question_message()

    def get_round_result(self):
        ans = ROUND_RESULT_TOPIC % self.state.player_counter

        for player in self.players.values():
            if not player.alive:
                continue
            ans += f" - {player.name} - {player.score} {POINTS_NAME}. (+{self.state.added_score})\n"

        ans += BANNED_PLAYERS_INFO % self.state.last_ban_amount
        logging.info(f"Round ended.\n{ans}")
        return ans

    def get_game_result(self, arena_num=0):
        if self.state.game_in_progress:
            return "Game still in progress."

        ans = GAME_RESULT_TOPIC % (
            self.state.question_answered, BATTLE_CHANNEL_TEMPLATE % (arena_num + 1))

        for player in self.players.values():
            if not player.alive:
                continue
            ans += f" - {player.name} - {player.score} {POINTS_NAME}.\n"

        ans += KICKED_PLAYERS_MESSAGE
        date = datetime.datetime.now().strftime("%d.%m.%Y")
        for player in self.state.dead_players:
            ans += f" F to {player.name}(?-{date}) - {player.score} {POINTS_NAME}.\n"
        ans += DIVADER
        logging.info(f"Round results.\n{ans}")
        return ans

    def get_start_quiz(self):
        if not self.state.game_in_progress:
            return f"This game is no longer active."

        ans = RULES_MESSAGE % (self.rounds_amount, self.answer_time)

        for player in self.players.values():
            ans += f" - {player.name} - {player.score} {POINTS_NAME}.\n"

        ans += GAME_TOPICS_INFO % self.topic[NAME_ACCESSOR]

        ans += CLICK_TO_START_MESSAGE
        logging.info(
            f"The game in {self.cid} with {self.state.player_counter} player is about to start")
        return ans

    def get_start_new_round(self):
        ans = ROUND_START_TOPIC % (
            self.state.question_answered + 1, self.state.dead_counter, self.state.player_counter)
        ans += self.get_question()
        self.state.last_ban_amount = 0
        logging.info(
            f"Round {self.state.question_answered} in {self.cid} started.")
        return ans

    def is_game_end(self):
        if self.state.player_counter <= 1:
            self.state.game_in_progress = False
        if self.state.question_answered == self.state.question_amount:
            self.state.game_in_progress = False

    def update_answer_statuses(self):
        for player in self.players.values():
            player.answered = False

    def record_round(self, answers):
        roundd = {}
        # bad code
        roundd[QUESTION_ID_ACCESSOR] = self.state.last_question.id
        roundd[ANSWERS_ACCESSOR] = []
        for uid, ans in answers.items():
            # bad code
            answer = {
                UID_ACCESSOR: uid,
                QUESTION_VARIANT: self.state.last_question.answers[ans - 1][2]
            }
            if self.state.last_question.answer == ans:
                answer[ANSWER_STATUS_ACCESSOR] = True
            else:
                answer[ANSWER_STATUS_ACCESSOR] = False
            roundd[ANSWERS_ACCESSOR].append(answer)
        self.state.rounds.append(roundd)

    def dump_game(self):
        answer = {}
        answer[PLAYERS_AMOUNT] = len(self.players)
        answer[DEAD_AMOUNT] = self.state.dead_counter
        answer[ROUNDS_AMOUNT] = self.state.question_answered
        answer[TOPIC_FIELD] = self.topic[ID_ACCESSOR]
        answer[DATETIME_FIELD] = datetime.datetime.now(
        ).strftime(DATETIME_TEMPLATE)
        answer[ROUNDS_ACCESSOR] = self.state.rounds
        answer[PLAYERS_MODELS_ACCESSOR] = [player.dump()
                                           for player in self.players.values()]  # wat
        return answer


class State(object):
    def __init__(self):
        self.dead_counter = 0
        self.player_counter = 0
        self.question_amount = 0
        self.question_answered = 0
        self.game_in_progress = True
        self.added_score = 1
        self.game_ended = False
        self.last_question = None
        self.last_ban_amount = 0
        self.dead_players = []
        self.rounds = []
