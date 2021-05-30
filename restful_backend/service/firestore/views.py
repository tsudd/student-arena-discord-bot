from threading import stack_size
from .firebase import *
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import logging

from .config import *

# Create your views here.


@api_view(["GET", "POST"])
def sessions_api(request):
    if request.method == 'POST':
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
            session = add_session_and_return(request.data)

            for p in data[PLAYERS_ACCESSOR]:
                save_player_and_part(p, session)

            add_rounds(data[ROUNDS_ACCESSOR], session)
        except ValueError:
            return Response(status=status.HTTP_410_GONE)
        return Response(status=status.HTTP_200_OK)
    elif request.method == "GET":
        params = dict(request.query_params)
        if ID_QUERY in params:
            session = get_session(params[ID_QUERY][0])
            if session is None:
                return Response(status=status.HTTP_204_NO_CONTENT)
            print(session)
            return Response(session)
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def session_info(request, pk):
    if request.method == "GET":
        session = get_session(pk)
        if session is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        print(session)
        return Response(session)


@api_view(["GET"])
def topics(request):
    if request.method == 'GET':
        return Response(get_topics())


@api_view(["GET"])
def questions(request):
    if request.method == "GET":
        params = dict(request.query_params)
        if AMOUNT_QUERY in params:
            amount = int(params[AMOUNT_QUERY][0])
        if TOPIC_QUERY in params:
            return Response(get_questions(params[TOPIC_QUERY][0], amount))
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def player_info(request, pk):
    if request.method == "GET":
        p = get_player(pk)
        if p is None:
            return Response(status=status.HTTP_204_NO_CONTENT)

        params = dict(request.query_params)
        amount = 10
        if AMOUNT_QUERY in params:
            amount = int(params[AMOUNT_QUERY])
        sessions = get_player_sessions(pk, amount)
        return Response({
            PLAYER_ACCESSOR: p,
            "sessions": sessions
        })
