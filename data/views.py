from django.http import Http404
from rest_framework import generics, status, permissions, views, mixins, viewsets
from rest_framework.response import Response
from django.db.models import Q, Case, When, Value, F, DecimalField, Subquery
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from uuid import uuid4

from .serializers import (
    MainDataSerializer, InformativeDataSerializer, FinancialDataSerializer, ObjectPhotoSerializer,
    MainDataRetrieveSerializer, InformativeDataRetrieveSerializer, FinancialDataRetrieveSerializer,
    MainDataDraftSerializer, InformativeDataDraftSerializer, FinancialDataDraftSerializer,
    AllDataSerializer, ObjectIdAndCoordinatesSerializer,  # InvestmentDraftSerializer,
    InvestorInfoSerializer, InvestorInfoGetSerializer, InvestorInfoGetMinimumSerializer,
    AllDataListSerializer, AllDataAllUsersListSerializer, CategorySerializer,
    LocationSerializer, ApproveRejectInvestorSerializer, InvestorInfoOwnSerializer,
    AllDataFilterSerializer, AreaSerializer, SmartNoteCreateSerializer, SmartNoteListRetrieveSerializer,
    SmartNoteUpdateSerializer, CurrencySerializer, CustomIdSerializer, FaqSerializer, InformativeProDataSerializer,
    AreaAPISerializer, CategoryApiSerializer, MainDataAPISerializer,
    AreaAPISerializer, CategoryApiSerializer, InformativeDataGetSerializer, AlldateCategorySerializer,
    CategoryApiProSerializer, CategoryApiProSerializer, AllDataProSerializer, CadastraInfoSerializer,
    ProductPhotoSerializer, CategoryApiProSerializer, CategoryApiProSerializer, AllDataProSerializer,
    CadastraInfoSerializer, ProductPhotoSerializer,
    CategoryApiProSerializer, CategoryApiProSerializer, AllDataProSerializer, CadastraInfoSerializer,
    ProductPhotoSerializer, AreaAPIDetailSerializer,

)
from .permissions import (
    IsLegal,
)
from .models import (
    Status, MainData, InformativeData, FinancialData, ObjectPhoto, AllData,
    InvestorInfo, Category, Area, SmartNote, CurrencyPrice, Currency, Faq, CadastralPhoto,
)
from utils.logs import log


class MainDataAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = MainDataAPISerializer
    permission_classes = (IsLegal,)
    lookup_field = 'user'

    def get_object(self):
        queryset = MainData.objects.filter(user=self.request.user, all_data__status=Status.DRAFT)
        try:
            instance = queryset.first()
        except MainData.DoesNotExist:
            raise Http404("No matching MainData found for this user")
        return instance

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class MainDataView(generics.CreateAPIView):
    serializer_class = MainDataSerializer
    permission_classes = (IsLegal,)

    def perform_create(self, serializer):
        instance = MainData.objects.filter(
            Q(user=self.request.user) &
            Q(all_data__status=Status.DRAFT)
        ).first()
        instance.is_validated = True
        for key, value in serializer.validated_data.items():
            setattr(instance, key, value)
        instance.save()


class InformativeDataView(generics.RetrieveUpdateAPIView):
    serializer_class = InformativeProDataSerializer
    permission_classes = (IsLegal,)

    def get_object(self):
        queryset = InformativeData.objects.filter(user=self.request.user, all_data__status=Status.DRAFT)
        try:
            instance = queryset.first()
        except InformativeData.DoesNotExist:
            raise Http404("No matching InformativeData found for this user")
        return instance

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # def perform_create(self, serializer):
    #     # Agar obyekt mavjud bo'lsa, uni o'chirib yangi obyekt yaratish kerak
    #     instance = InformativeData.objects.filter(
    #         Q(user=self.request.user) &
    #         Q(all_data__status=Status.DRAFT)
    #     ).first()
    #     if instance:
    #         instance.delete()  # Avvalgi ma'lumotni o'chiramiz
    #         serializer.save(user=self.request.user, is_validated=True)
    #         all_data = AllData.objects.get(user=self.request.user)
    #         all_data.informative_data = InformativeData.objects.last()
    #         all_data.save()


class ObjectPhotoView(generics.CreateAPIView):
    serializer_class = ObjectPhotoSerializer
    permission_classes = (IsLegal,)

    def perform_create(self, serializer):
        instance = InformativeData.objects.filter(
            Q(user=self.request.user) &
            Q(all_data__status=Status.DRAFT)
        ).first()
        ObjectPhoto.objects.create(
            image=serializer.validated_data['image'],
            informative_data=instance
        )


class FinancialDataView(generics.CreateAPIView):
    serializer_class = FinancialDataSerializer
    permission_classes = (IsLegal,)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        # log('StartLog')
        if serializer.is_valid():
            instance = FinancialData.objects.filter(
                Q(user=self.request.user) &
                Q(all_data__status=Status.DRAFT)
            ).first()
            instance.is_validated = True
            # setattr(instance, 'is_validated', True)
            for key, value in serializer.validated_data.items():
                setattr(instance, key, value)
            # log(f'is_validated: {instance.is_validated}')
            instance.save()

            all_data = AllData.objects.filter(
                Q(user=self.request.user) &
                Q(status=Status.DRAFT) &
                Q(main_data__is_validated=True) &
                Q(informative_data__is_validated=True) &
                Q(financial_data__is_validated=True)
            )
            # log(f'all_data: {all_data.id}')
            if all_data.exists():
                all_data = all_data.first()
                all_data.status = Status.CHECKING # VAXTINCHALIK OZGARTRIB TUSHILGAN SINOV UCHUNCHECKING
                all_data.save()
                # log(f'all_data2: {all_data.status}')

                main_data = MainData.objects.create(
                    user=self.request.user,
                )
                informative_data = InformativeData.objects.create(
                    user=self.request.user,
                )
                financial_data = FinancialData.objects.create(
                    user=self.request.user, currency=Currency.objects.first()
                )
                AllData.objects.create(
                    main_data=main_data,
                    informative_data=informative_data,
                    financial_data=financial_data,
                    user=self.request.user
                )
                return Response(serializer.validated_data)
            else:
                return Response({'error': 'Not all data validated'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FinancialDataAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = FinancialDataSerializer

    permission_classes = (IsLegal,)

    def get_object(self):
        queryset = FinancialData.objects.filter(user=self.request.user)
        try:
            instance = queryset.first()
        except FinancialData.DoesNotExist:
            raise Http404("No matching FinancialData found for this user")
        return instance

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            all_data = AllData.objects.filter(
                Q(user=self.request.user) &
                Q(status=Status.DRAFT) &
                Q(main_data__is_validated=True) &
                Q(informative_data__is_validated=True) &
                Q(financial_data__is_validated=True)
            )
            if all_data.exists():
                all_data = all_data.first()
                all_data.status = Status.CHECKING  # VAXTINCHALIK OZGARTRIB TUSHILGAN SINOV UCHUN
                all_data.save()

                main_data = MainData.objects.create(
                    user=self.request.user,
                )
                informative_data = InformativeData.objects.create(
                    user=self.request.user,
                )

                financial_data = FinancialData.objects.create(
                    user=self.request.user,
                    currency=Currency.objects.first()
                )
                AllData.objects.create(
                    main_data=main_data,
                    informative_data=informative_data,
                    financial_data=financial_data,
                    user=self.request.user
                )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response({'error': 'Not all data validated'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # def create(self, request, *args, **kwargs):

    # all_data = AllData.objects.filter(
    #     Q(user=self.request.user) &
    #     Q(status=Status.DRAFT) &
    #     Q(main_data__is_validated=True) &
    #     Q(informative_data__is_validated=True) &
    #     Q(financial_data__is_validated=True)
    # )
    # if all_data.exists():
    #     all_data = all_data.first()
    #     all_data.status = Status.CHECKING # VAXTINCHALIK OZGARTRIB TUSHILGAN SINOV UCHUN
    #     all_data.save()
    #
    #     main_data = MainData.objects.create(
    #         user=self.request.user,
    #     )
    #     informative_data = InformativeData.objects.create(
    #         user=self.request.user,
    #     )
    #
    #     financial_data = FinancialData.objects.create(
    #         user=self.request.user,
    #         currency=Currency.objects.first()
    #     )
    #     AllData.objects.create(
    #         main_data=main_data,
    #         informative_data=informative_data,
    #         financial_data=financial_data,
    #         user=self.request.user
    #     )
    #     return Response(status=status.HTTP_201_CREATED)
    # else:
    #     return Response({'error': 'Not all data validated'}, status=status.HTTP_400_BAD_REQUEST)


class MainDataDraftRetrieveView(generics.RetrieveAPIView):
    serializer_class = MainDataRetrieveSerializer
    permission_classes = (IsLegal,)

    def get_object(self):
        return MainData.objects.filter(Q(all_data__status=Status.DRAFT) & Q(user=self.request.user)).first()
        return MainData.objects.all()


class MainDataDraftListView(generics.RetrieveAPIView):
    serializer_class = MainDataRetrieveSerializer
    permission_classes = (IsLegal,)

    def get_object(self):
        queryset = MainData.objects.filter(user=self.request.user)
        try:
            instance = queryset.first()
        except MainData.DoesNotExist:
            raise Http404("No matching MainData found for this user")
        return instance


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (permissions.AllowAny,)


class AreaListView(generics.ListAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = (permissions.AllowAny,)


class AreaAPIListView(generics.ListAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaAPISerializer
    # permission_classes = (permissions.AllowAny,)


class CategoryApiListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategoryApiProSerializer
    permission_classes = (permissions.AllowAny,)


class CategoryRetrieveView(generics.RetrieveAPIView):
    queryset = Category.objects.all()
    serializer_class = CategoryApiProSerializer
    permission_classes = (permissions.AllowAny,)

    # def get(self, request, *args, **kwargs):
    #     queryset = AllData.objects.all()  # Sizning queryset
    #     serializer = AlldateCategorySerializer()
    #     return Response(serializer.data)


class AllDataCatListAPIView(generics.ListAPIView):
    queryset = AllData.objects.all()
    serializer_class = AlldateCategorySerializer
    permission_classes = (permissions.AllowAny,)

    # def get_queryset(self):
    #     category = self.kwargs['category']
    #     obj_main = AllData.objects.filter(main_data__category=category)


class CurrencyListView(generics.ListAPIView):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = (permissions.AllowAny,)


class InformativeDataDraftRetrieveView(generics.RetrieveAPIView):
    serializer_class = InformativeDataGetSerializer
    permission_classes = (IsLegal,)

    def get_object(self):
        return InformativeData.objects.filter(Q(all_data__status=Status.DRAFT) & Q(user=self.request.user)).first()


class FinancialDataDraftRetrieveView(generics.RetrieveAPIView):
    serializer_class = FinancialDataRetrieveSerializer
    permission_classes = (IsLegal,)

    def get_object(self):
        return FinancialData.objects.filter(Q(all_data__status=Status.DRAFT) & Q(user=self.request.user)).first()


class AllDataViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    queryset = AllData.objects.filter(status=Status.APPROVED)
    permission_classes = (permissions.AllowAny,)
    serializer_class = AllDataSerializer


class AllDataUserViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    queryset = AllData.objects.all()
    permission_classes = (IsLegal,)
    # serializer_class = AllDataListSerializer
    default_serializer_class = AllDataSerializer
    serializer_classes = {
        'list': AllDataListSerializer,
        'retrieve': AllDataSerializer
    }

    def get_queryset(self):
        return AllData.objects.filter(~Q(status=Status.DRAFT) & Q(user=self.request.user))

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)


class AllDataUserViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    queryset = AllData.objects.all()
    permission_classes = (IsLegal,)
    # serializer_class = AllDataListSerializer
    default_serializer_class = AllDataSerializer
    serializer_classes = {
        'list': AllDataListSerializer,
        'retrieve': AllDataSerializer
    }

    def get_queryset(self):
        return AllData.objects.filter(~Q(status=Status.DRAFT) & Q(user=self.request.user))

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)


class AllDataAllUsersViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    queryset = AllData.objects.all()
    permission_classes = (IsLegal,)
    # serializer_class = AllDataListSerializer
    default_serializer_class = AllDataSerializer
    serializer_classes = {
        'list': AllDataAllUsersListSerializer,
        'retrieve': AllDataSerializer
    }

    def get_queryset(self):
        return AllData.objects.filter(Q(status=Status.APPROVED))

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)


class CustomAlldataAllUsersListView(generics.ListAPIView):
    queryset = AllData.objects.filter(Q(status=Status.APPROVED))
    serializer_class = AllDataAllUsersListSerializer
    permission_classes = (permissions.AllowAny,)

    def list(self, request, *args, **kwargs):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        assert lookup_url_kwarg in self.kwargs, (
                'Expected view %s to be called with a URL keyword argument '
                'named "%s". Fix your URL conf, or set the `.lookup_field` '
                'attribute on the view correctly.' %
                (self.__class__.__name__, lookup_url_kwarg)
        )
        filter_kwargs = {'main_data__category__id': self.kwargs[lookup_url_kwarg]}
        queryset = self.queryset.filter(**filter_kwargs)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# class MainDataApprovedRetrieveView(generics.RetrieveAPIView):
#     serializer_class = MainDataRetrieveSerializer
#     permission_classes = (IsLegal,)

#     def get_object(self):
#         return MainData.objects.filter(user=self.request.user).first()


# class InformativeDataApprovedRetrieveView(generics.RetrieveAPIView):
#     serializer_class = InformativeDataRetrieveSerializer
#     permission_classes = (IsLegal,)

#     def get_object(self):
#         return InformativeData.objects.filter(user=self.request.user).first()


# class FinancialDataApprovedRetrieveView(generics.RetrieveAPIView):
#     serializer_class = FinancialDataRetrieveSerializer
#     permission_classes = (IsLegal,)

#     def get_object(self):
#         return FinancialData.objects.filter(user=self.request.user).first()


# class SetReadyStatusView(views.APIView):
#     permission_classes = (IsLegal,)

#     def post(self, request):
#         all_data = AllData.objects.filter(user=request.user).first()
#         all_data.status = Status.READY
#         all_data.save()
#         return Response()


class MainDataDraftView(generics.CreateAPIView):
    serializer_class = MainDataDraftSerializer
    permission_classes = (IsLegal,)

    def perform_create(self, serializer):
        hasnot_instance = False
        instance = MainData.objects.filter(
            Q(user=self.request.user) &
            Q(all_data__status=Status.DRAFT)
        ).first()
        if instance is None:
            hasnot_instance = True
            instance = MainData(user=self.request.user)
        for key, value in serializer.validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if hasnot_instance:
            informdata = InformativeData(user=self.request.user)
            informdata.save()
            finandata = FinancialData(user=self.request.user, currency=Currency.objects.first())
            finandata.save()
            all_data = AllData(main_data=instance, informative_data=informdata,
                               financial_data=finandata, user=self.request.user,
                               )
            all_data.save()


class InformativeDataDraftView(generics.CreateAPIView):
    serializer_class = InformativeDataDraftSerializer
    permission_classes = (IsLegal,)

    def perform_create(self, serializer):
        instance = InformativeData.objects.filter(
            Q(user=self.request.user) &
            Q(all_data__status=Status.DRAFT)
        ).first()
        for key, value in serializer.validated_data.items():
            setattr(instance, key, value)
        instance.save()


class FinancialDataDraftView(generics.CreateAPIView):
    serializer_class = FinancialDataDraftSerializer
    permission_classes = (IsLegal,)

    def perform_create(self, serializer):
        instance = FinancialData.objects.filter(
            Q(user=self.request.user) &
            Q(all_data__status=Status.DRAFT)
        ).first()
        for key, value in serializer.validated_data.items():
            setattr(instance, key, value)
        instance.save()


# class InvestmentDraftView(generics.CreateAPIView):
#     serializer_class = InvestmentDraftSerializer
#     permission_classes = (IsLegal,)

#     def perform_create(self, serializer):
#         all_data = AllData.objects.filter(
#             Q(all_data=serializer.validated_data['all_data']) &
#             Q(status=Status.APPROVED)
#         )

#         if all_data.exists():
#             instance = FinancialData.objects.filter(
#                 Q(investor=self.request.user) &
#                 Q(status=Status.DRAFT)
#             )

#             if not instance.exists():
#                 instance = Investment.objects.create(
#                     investor=self.request.user,
#                     status=Status.DRAFT
#                 )
#             else:
#                 instance = instance.first()

#             for key, value in serializer.validated_data.items():
#                 setattr(instance, key, value)
#             instance.save()


class InvestorInfoView(generics.CreateAPIView):
    serializer_class = InvestorInfoSerializer
    permission_classes = (IsLegal,)

    def perform_create(self, serializer):
        all_data = AllData.objects.filter(
            Q(id=serializer.validated_data['all_data'].id) &
            Q(status=Status.APPROVED)
        )

        if all_data.exists():
            instance = InvestorInfo.objects.create(
                investor=self.request.user,
                status=Status.APPROVED,
                all_data=all_data.first()
            )

            for key, value in serializer.validated_data.items():
                if not key == 'all_data':
                    setattr(instance, key, value)
            instance.save()


class InvestorInfoViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    queryset = InvestorInfo.objects.all()
    permission_classes = (IsLegal,)
    serializer_class = InvestorInfoGetSerializer

    def get_queryset(self):
        return InvestorInfo.objects.filter(
            Q(status=Status.APPROVED) &
            Q(all_data__user=self.request.user)
        )


user_id = openapi.Parameter(
    'user_id', openapi.IN_QUERY,
    description="If user_id exists, return investors for this user, else return investors for current user",
    type=openapi.TYPE_STRING
)


@method_decorator(name='list', decorator=swagger_auto_schema(manual_parameters=[
    user_id,
]))
class AllObjectInvestorsViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    queryset = InvestorInfo.objects.all()
    permission_classes = (IsLegal,)
    # serializer_class = InvestorInfoGetSerializer
    default_serializer_class = InvestorInfoGetSerializer
    serializer_classes = {
        'list': InvestorInfoGetMinimumSerializer,
        'retrieve': InvestorInfoGetSerializer
    }

    def get_serializer_class(self):
        return self.serializer_classes.get(self.action, self.default_serializer_class)

    def get_queryset(self):
        data = self.request.GET.dict()
        queryset = ~Q(status=Status.DRAFT)
        if 'user_id' in data:
            queryset &= Q(all_data__user__id=data['user_id'])
        else:
            queryset &= Q(all_data__user=self.request.user)
        return InvestorInfo.objects.filter(queryset)


class ObjectIdAndCoordinatesViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    queryset = AllData.objects.filter(status=Status.APPROVED)
    permission_classes = (permissions.AllowAny,)
    serializer_class = ObjectIdAndCoordinatesSerializer


from geopy.geocoders import Nominatim


# Tushunarli location malumotlari

class LocationView(generics.CreateAPIView):
    serializer_class = LocationSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            geolocator = Nominatim(user_agent="E-Investment")
            location = geolocator.reverse(f"{serializer.validated_data['lat']}, {serializer.validated_data['long']}")
            return Response(location.address)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# tushunmadim hozrcha
class ApproveRejectView(generics.CreateAPIView):
    serializer_class = ApproveRejectInvestorSerializer
    permission_classes = (IsLegal,)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            investor = InvestorInfo.objects.filter(
                Q(id=serializer.validated_data['investor_id']) &
                Q(all_data__id=serializer.validated_data['all_data_id'])
            )
            if investor.exists():
                investor = investor.first()
                if serializer.validated_data['is_approve']:
                    investor.status = Status.APPROVED
                else:
                    investor.status = Status.REJECTED
                investor.save(force_update=True)
                return Response(serializer.validated_data)
            else:
                return Response({'error': 'Investor or object does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvestorInfoOwnListView(generics.ListAPIView):
    queryset = InvestorInfo.objects.all()
    serializer_class = InvestorInfoOwnSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return InvestorInfo.objects.filter(investor=self.request.user)


# tastiqdan otgan

categories = openapi.Parameter(
    'categories', openapi.IN_QUERY,
    description="Filter objects by array of categories id. Example: categories=1,2",
    type=openapi.TYPE_STRING
)


# tastiqdan otgan
@method_decorator(name='get', decorator=swagger_auto_schema(manual_parameters=[
    categories,
]))
class AllDataFilterView(generics.ListAPIView):
    serializer_class = AllDataFilterSerializer
    permission_classes = (permissions.AllowAny,)

    # pagination_class = TenPagesPagination

    def get_queryset(self):
        data = self.request.GET.dict()
        queryset = Q(status=Status.APPROVED)

        if 'categories' in data:
            category_list = list(map(int, data['categories'].split(',')))
            queryset &= Q(main_data__category__pk__in=category_list)

        if 'locations' in data:
            location_list = []
            for location in data['locations'].split(','):
                location_list.append(int(location))
            queryset &= Q(main_data__location__pk__in=location_list)

        startprice = data.get('startprice', None)
        endprice = data.get('endprice', None)

        if startprice and endprice:
            queryset &= Q(new_price_dollar__gte=int(startprice), new_price_dollar__lte=int(endprice))
        elif startprice:  # faqat startprice bo'lsa
            queryset &= Q(new_price_dollar__gte=int(startprice))

        datas = AllData.objects.annotate(
            latest_gbp_price=Subquery(CurrencyPrice.objects.filter(code='GBP').order_by('-date').values('cb_price')[:1],
                                      output_field=DecimalField(max_digits=18, decimal_places=2)),
            latest_eur_price=Subquery(CurrencyPrice.objects.filter(code='EUR').order_by('-date').values('cb_price')[:1],
                                      output_field=DecimalField(max_digits=18, decimal_places=2)),
            latest_usd_price=Subquery(CurrencyPrice.objects.filter(code='USD').order_by('-date').values('cb_price')[:1],
                                      output_field=DecimalField(max_digits=18, decimal_places=2)),
        ).annotate(
            new_price_dollar=Case(
                When(financial_data__currency__code='GBP',
                     then=F('financial_data__authorized_capital') * F('latest_gbp_price') / F('latest_usd_price')),
                When(financial_data__currency__code='EUR',
                     then=F('financial_data__authorized_capital') * F('latest_eur_price') / F('latest_usd_price')),
                When(financial_data__currency__code='UZS',
                     then=F('financial_data__authorized_capital') / F('latest_usd_price')),
                When(financial_data__currency__code='USD',
                     then=F('financial_data__authorized_capital') * F('latest_usd_price') / F('latest_usd_price')),
                default=F('financial_data__authorized_capital'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            )
        ).filter(queryset)
        return datas


# tastiqdan otgan

import math

lat_long = openapi.Parameter(
    'lat_long', openapi.IN_QUERY,
    description="Filter objects by latitude and longitude. Example: lat_long=21.1234,22.4321",
    type=openapi.TYPE_STRING
)
distance_km = openapi.Parameter(
    'distance', openapi.IN_QUERY,
    description="Filter objects by radius in km from latitude and longitude. Example: distance=10. Default distance 50 km",
    type=openapi.TYPE_STRING
)


# tastiqdan otgan

@method_decorator(name='get', decorator=swagger_auto_schema(manual_parameters=[
    lat_long, distance_km
]))
class AllDataFilterByLatLongDistanceView(generics.ListAPIView):
    serializer_class = AllDataFilterSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        data = self.request.GET.dict()
        queryset = Q(status=Status.APPROVED)

        distance = 50.0
        earth_radius = 6371.0
        if 'distance' in data:
            distance = float(data['distance']) if distance <= earth_radius else earth_radius

        if 'lat_long' in data:
            lat_long_list = data['lat_long'].split(',')
            if len(lat_long_list) == 2:
                lat = float(lat_long_list[0])
                long = float(lat_long_list[1])
                max_lat = lat + math.degrees(distance / earth_radius)
                min_lat = lat - math.degrees(distance / earth_radius)
                max_long = long + math.degrees(math.asin(distance / earth_radius) / math.cos(math.radians(lat)))
                min_long = long - math.degrees(math.asin(distance / earth_radius) / math.cos(math.radians(lat)))
                # log(f'min_lat: {min_lat} max_lat: {max_lat} min_long: {min_long} max_long: {max_long}')
                queryset &= Q(main_data__lat__gte=min_lat)
                queryset &= Q(main_data__lat__lte=max_lat)
                queryset &= Q(main_data__long__gte=min_long)
                queryset &= Q(main_data__long__lte=max_long)
                return AllData.objects.filter(queryset)
            else:
                return []
        return []


class SmartNoteCreateView(generics.CreateAPIView):
    serializer_class = SmartNoteCreateSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        custom_id = serializer.validated_data.get('custom_id')
        if self.request.user.is_authenticated:
            instance = SmartNote(user=self.request.user)
            if custom_id != '':
                notes = SmartNote.objects.filter(
                    custom_id=custom_id,
                    user__isnull=True
                )
                if notes.exists():
                    notes.update(user=self.request.user)
        else:
            if custom_id == '':
                custom_id = str(uuid4())[-12:]
            instance = SmartNote(custom_id=custom_id)

        # Serializer yordamida saqlash
        instance = serializer.save(user=self.request.user if self.request.user.is_authenticated else None,
                                   custom_id=custom_id)

        # Javobda qaytarish
        data_for_return = SmartNoteCreateSerializer(instance)
        headers = self.get_success_headers(serializer.data)
        return Response(data_for_return.data, status=status.HTTP_201_CREATED, headers=headers)


from rest_framework.response import Response
from rest_framework import status


class SmartNoteListView(generics.ListAPIView):
    queryset = SmartNote.objects.all()
    serializer_class = SmartNoteListRetrieveSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = CustomIdSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        if self.request.user.is_authenticated:
            if SmartNote.objects.filter(user=self.request.user):
                datas = SmartNote.objects.filter(user=self.request.user).select_related('main_data')
            else:
                custom_id = serializer.validated_data.get('custom_id')
                if custom_id != '':
                    datas = SmartNote.objects.filter(custom_id=custom_id).select_related('main_data')
                else:
                    datas = None
        else:
            custom_id = serializer.validated_data.get('custom_id')
            if custom_id != '':
                datas = SmartNote.objects.filter(custom_id=custom_id).select_related('main_data')
            else:
                datas = None

        serializer_info = SmartNoteListRetrieveSerializer(datas, many=True)
        return Response(serializer_info.data, status=status.HTTP_200_OK)


class SmartNoteRetrieveView(generics.CreateAPIView):
    serializer_class = SmartNoteListRetrieveSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = CustomIdSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        assert lookup_url_kwarg in self.kwargs, (
                'Expected view %s to be called with a URL keyword argument '
                'named "%s". Fix your URL conf, or set the `.lookup_field` '
                'attribute on the view correctly.' %
                (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        queryset = Q(status=Status.APPROVED)
        if self.request.user.is_authenticated:
            queryset = Q(user=self.request.user)
        else:
            custom_id = serializer.validated_data.get('custom_id')
            if custom_id != '':
                queryset = Q(custom_id=custom_id)
            else:
                queryset = Q(user__id=-985)
        datas = SmartNote.objects.filter(queryset, **filter_kwargs).select_related('main_data').first()

        serializer_info = SmartNoteListRetrieveSerializer(datas, context={'request': request})

        headers = self.get_success_headers(serializer.data)
        return Response(serializer_info.data, status=status.HTTP_200_OK, headers=headers)




class SmartNoteDestroyView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = CustomIdSerializer

    def post(self, request, *args, **kwargs):
        serializer = CustomIdSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
                'Expected view %s to be called with a URL keyword argument '
                'named "%s". Fix your URL conf, or set the `.lookup_field` '
                'attribute on the view correctly.' %
                (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        if self.request.user.is_authenticated:
            queryset = Q(user=self.request.user)
        else:
            custom_id = serializer.validated_data.get('custom_id')
            if custom_id != '':
                queryset = Q(custom_id=custom_id)
            else:
                queryset = Q(user__id=-985)
        instance = SmartNote.objects.filter(queryset, **filter_kwargs).first()
        if instance is not None:
            # Images va videos bo'lsa, o'chirish
            if instance.images.exists():
                instance.images.all().delete()  # Barcha bog'langan rasmlarni o'chirish
            if instance.videos.exists():
                instance.videos.all().delete()  # Barcha bog'langan videolarni o'chirish
            # SmartNote instance'ini o'chirish
            instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SmartNoteUpdateView(generics.CreateAPIView):
    serializer_class = SmartNoteUpdateSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        assert lookup_url_kwarg in self.kwargs, (
                'Expected view %s to be called with a URL keyword argument '
                'named "%s". Fix your URL conf, or set the `.lookup_field` '
                'attribute on the view correctly.' %
                (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}

        # Foydalanuvchi autentifikatsiyasi
        if self.request.user.is_authenticated:
            queryset = Q(user=self.request.user)
        else:
            custom_id = request.data.get('custom_id')  # serializer.validated_data o'rniga request.data
            if custom_id != '':
                queryset = Q(custom_id=custom_id)
            else:
                queryset = Q(user__id=-985)

        instance = SmartNote.objects.filter(queryset, **filter_kwargs).first()

        if instance:
            # Serializerni validatsiya qilish
            serializer = self.get_serializer(instance, data=request.data, partial=True)  # partial=True - qisman yangilash
            serializer.is_valid(raise_exception=True)

            # Yangilash jarayonini amalga oshirish
            self.perform_update(serializer)

            updated_serializer = self.get_serializer(instance)
            headers = self.get_success_headers(updated_serializer.data)
            return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)
        else:
            return Response({"detail": "Smart Note not found."}, status=status.HTTP_404_NOT_FOUND)

    def perform_update(self, serializer):
        serializer.save()  # Serializer orqali yangilash

class FaqRetriveView(generics.ListAPIView):
    queryset = Faq.objects.all()
    serializer_class = FaqSerializer
    permission_classes = (permissions.AllowAny,)

    def list(self, request, *args, **kwargs):
        queryset = Faq.objects.first()
        serializer = self.get_serializer(queryset)
        return Response(serializer.data)


# ADASBEK
class ObjectPhotoViewList(generics.ListAPIView):
    queryset = ObjectPhoto.objects.all()
    serializer_class = ObjectPhotoSerializer
    permission_classes = (permissions.AllowAny,)


class AreaAPIDeatilView(generics.RetrieveAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaAPIDetailSerializer
    permission_classes = (permissions.AllowAny,)


class AreaMainAPIListView(generics.ListAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaAPIDetailSerializer
    permission_classes = (permissions.AllowAny,)
