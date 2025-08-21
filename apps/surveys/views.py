from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .models import Survey, SurveySection, SurveyQuestion, SurveyQuestionOption, LogicRule
from .serializers import (
    SurveyCreateSerializer, SurveyListSerializer, SurveyDetailSerializer,
    SectionCreateSerializer, QuestionCreateSerializer,
    OptionCreateSerializer, OptionBulkCreateSerializer, LogicRuleCreateSerializer
)

class SurveyListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Survey.objects.all().order_by("id")
        return Response(SurveyListSerializer(qs, many=True).data)

    def post(self, request):
        ser = SurveyCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        survey = ser.save()
        return Response(SurveyDetailSerializer(survey).data, status=status.HTTP_201_CREATED)

class SurveyDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, survey_id: int):
        survey = get_object_or_404(Survey.objects.prefetch_related(
            "sections__questions__options"
        ), pk=survey_id)
        return Response(SurveyDetailSerializer(survey).data)

class SectionCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, survey_id: int):
        survey = get_object_or_404(Survey, pk=survey_id)
        ser = SectionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        section = ser.save(survey=survey)
        return Response({"id": section.id}, status=status.HTTP_201_CREATED)

class QuestionCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, section_id: int):
        section = get_object_or_404(SurveySection, pk=section_id)
        ser = QuestionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        question = ser.save(section=section)
        return Response({"id": question.id}, status=status.HTTP_201_CREATED)

class OptionCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, question_id: int):
        question = get_object_or_404(SurveyQuestion, pk=question_id)

        # support both single and bulk payloads
        if isinstance(request.data, dict) and "options" in request.data:
            bulk_ser = OptionBulkCreateSerializer(data=request.data)
            bulk_ser.is_valid(raise_exception=True)
            created = []
            for item in bulk_ser.validated_data["options"]:
                obj = SurveyQuestionOption.objects.create(question=question, **item)
                created.append(obj.id)
            return Response({"created_ids": created}, status=status.HTTP_201_CREATED)
        else:
            ser = OptionCreateSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            opt = ser.save(question=question)
            return Response({"id": opt.id}, status=status.HTTP_201_CREATED)

class LogicRuleCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, survey_id: int):
        survey = get_object_or_404(Survey, pk=survey_id)
        ser = LogicRuleCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rule = ser.save(survey=survey)
        return Response({"id": rule.id}, status=status.HTTP_201_CREATED)
