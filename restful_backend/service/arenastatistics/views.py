from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status

from .serializers import *
from .models import *

from .config import *

import random
import logging

# import firebase_admin
# from firebase_admin import firestore
# from firebase_admin import credentials

# # Create your views here.
# # Use a service account
# cred = credentials.Certificate(
#     '/home/appuser/project/arenastatistics/farebase/sudent-arena-bot-firebase-adminsdk-ps8j6-7da2d15a35.json')
# default = firebase_admin.initialize_app(cred, name="app")
# db = firestore.client(default)


class TopicsList(generics.ListAPIView):
    serializer_class = QuestionTopicSerializer
    queryset = QuestionTopic.objects.all()


class QuestionsList(generics.ListAPIView):
    serializer_class = QuestionSerializer
    queryset = Question.objects.all()

    def get(self, request, *args, **kwargs):
        params = dict(request.query_params)
        amount = 10
        questions = []
        if AMOUNT_QUERY in params:
            amount = int(params[AMOUNT_QUERY][0])
        if TOPIC_QUERY in params:
            topic_id = int(params[TOPIC_QUERY][0])
            all_questions = list(Question.objects.filter(topic__id=topic_id))
            random.shuffle(all_questions)
            if len(all_questions) >= amount:
                questions = all_questions[:amount]
            else:
                questions = all_questions
            logging.info(
                f"Sending questions list by params: amount - {amount}, topic - {topic_id}")
            return Response(
                self.serializer_class(
                    questions, many=True, context=self.get_serializer_context()).data
            )
        else:
            return super().get(request, args, kwargs)


class SessionsList(generics.ListCreateAPIView):
    serializer_class = SessionSerializer
    queryset = Session.objects.all()

    def get_player_or_default(self, player: dict) -> Player:
        player_obj = None
        try:
            player_obj = Player.objects.get(dis_id=player[ID_ACCESSOR])
        except:
            player_obj = Player()
            player_obj.dis_id = player[ID_ACCESSOR]
            player_obj.nick = player[NAME_ACCESSOR]
        return player_obj

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            assert DEAD_AMOUNT in data and \
                PLAYERS_AMOUNT in data and \
                TOPIC_FIELD in data and \
                DATETIME_FIELD in data and \
                ROUNDS_AMOUNT in data and \
                ROUNDS_ACCESSOR in data and \
                PLAYERS_ACCESSOR in data
        except AssertionError:
            logging.error("Bad data in POST request.")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            logging.info("Saving session.")
            session = Session(
                players_amount=data[PLAYERS_AMOUNT],
                dead_amount=data[DEAD_AMOUNT],
                rounds_amount=data[ROUNDS_AMOUNT],
                date=data[DATETIME_FIELD],
                topic=QuestionTopic.objects.get(pk=data[TOPIC_FIELD])
            )
            session.save()

            players = {}
            for p in data[PLAYERS_ACCESSOR]:
                players[p[ID_ACCESSOR]] = self.get_player_or_default(p), p

            logging.info("Saving players")
            for p in players.values():
                if p[1][ALIVE_ACCESSOR]:
                    p[0].wins += 1
                p[0].update_lifetime(
                    p[1][TOTAL_RIGHTS_ACCESSOR],
                    session.rounds_amount,
                    p[1][ALIVE_ACCESSOR]
                )
                p[0].save()

            logging.info("Saving rounds and answers")
            for r in data[ROUNDS_ACCESSOR]:
                roun = Round(
                    session=session,
                    question=Question.objects.get(pk=r[QUESTION_ID_ACCESSOR]),
                    first_variant=QuestionVariant.objects.get(
                        pk=r[QUESTION_ANSWERS_FIELDS[0]]),
                    second_variant=QuestionVariant.objects.get(
                        pk=r[QUESTION_ANSWERS_FIELDS[1]]),
                    three_variant=QuestionVariant.objects.get(
                        pk=r[QUESTION_ANSWERS_FIELDS[2]]),
                    four_variant=QuestionVariant.objects.get(
                        pk=r[QUESTION_ANSWERS_FIELDS[3]]),
                    right_ind=r[QUESTION_RIGHT_ANSWER]
                )
                roun.save()
                for ans in r[ANSWERS_ACCESSOR]:
                    answer = Answer(
                        session=session,
                        round=roun,
                        player=players[ans[UID_ACCESSOR]][0],
                        answer=QuestionVariant.objects.get(
                            pk=ans[QUESTION_VARIANT]),
                        right=ans[ANSWER_STATUS_ACCESSOR]
                    )
                    answer.save()
            logging.info("Saving participation")
            for p in players.values():
                part = Participation(session=session, player=p[0])
                part.save()
            return Response(status=status.HTTP_201_CREATED)
        except Exception as e:
            logging.info(f"Exception while saving data: {e}")
            return Response(status=status.HTTP_400_BAD_REQUEST)


class PlayerDetail(generics.ListAPIView):
    serializer_class = PlayerSerializer
    queryset = Player.objects.all()

    def get(self, request, *args, **kwargs):
        params = dict(request.query_params)
        if len(params) == 0:
            return super().get(request, args, kwargs)
        uid = None
        if ID_QUERY in params:
            uid = int(params[ID_QUERY][0])
        else:
            raise AssertionError
        amount = 10
        if AMOUNT_QUERY in params:
            amount = int(params[AMOUNT_QUERY][0])
        player = Player.objects.get(dis_id=uid)
        parts = list(Participation.objects.filter(
            player=player).order_by("session__date")[:amount].values("session_id"))
        ids = [record["session_id"] for record in parts]
        sessions = Session.objects.filter(pk__in=ids)
        return Response({
            "player": self.serializer_class(player, context=self.get_serializer_context()).data,
            "sessions": SessionSerializer(sessions, many=True, context=self.get_serializer_context()).data
        })


class SessionDetail(generics.RetrieveAPIView):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer

    def get(self, request, *args, **kwargs):
        params = kwargs
        try:
            pk = params["pk"]
            session = Session.objects.get(pk=pk)
            round_objects = list(Round.objects.filter(session__id=pk))
            rounds = []
            for r in round_objects:
                anses = AnswerSerializer(
                    list(Answer.objects.filter(round__id=r.id)), many=True).data
                rr = RoundSerializer(r).data
                rr.update({
                    "answers": anses
                })
                rounds.append(rr)

        except ObjectDoesNotExist:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {**self.serializer_class(
                session, context=self.get_serializer_context()).data,
                "rounds": rounds})
