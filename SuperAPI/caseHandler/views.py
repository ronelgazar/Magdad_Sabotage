from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from django.http.response import JsonResponse
from django.http.response import FileResponse
from django.db.models import Value
from django.http.response import HttpResponse
from django.http import Http404
from django.db.models import Max
from django.utils.translation import ugettext
from io import BytesIO
import xlsxwriter
from datetime import datetime
from datetime import date

from django.db.models import Value

from caseHandler.models import Case
from caseHandler.serializers import CaseSerializer
from caseHandler.serializers import CaseSerializerI

from caseHandler.models import Exhibits
from caseHandler.serializers import ExhibitsSerializer
from caseHandler.serializers import ExhibitsSerializerI

from caseHandler.models import Samples
from caseHandler.serializers import SamplesSerializer

from docsCreate.docx_generator import generate_docx
from django.core.files.storage import default_storage

from caseHandler.create_default_values import create_default_values, DEFAULT_VALUE


# The fuction return list of cases between choosen dates in the case list it gets
def filterDate(case_list, query_data, date_format='%Y-%m-%dT%H:%M:%S.%f%z', filter_by_status_closed_date=False):
    if "min_date" in query_data and "" != query_data['min_date']:
        min_date = datetime.strptime(query_data['min_date'], date_format)
    else:
        min_date = datetime.min
    if "max_date" in query_data and "" != query_data['max_date']:
        max_date = datetime.strptime(query_data['max_date'], date_format)
    else:
        max_date = datetime.max
    res = []
    for case in case_list:
        if filter_by_status_closed_date:
            if case.status_closed_date == "default":
                continue
            case_date = datetime.strptime(case.status_closed_date, date_format)
        else:
            if case.event_date == "default":
                continue
            case_date = datetime.strptime(case.event_date, '%Y-%m-%dT%H:%M:%S.%f%z')

        if min_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None) <= \
                case_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None) <= \
                max_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
            res.append(case)
    # returns new case querySet object
    return res


# The function return monthly summery(by dates)
def monthly_sum(dates, get_dict=False):  # more updates will come

    case_list = []
    count = 0
    result = {"totalOpenCases": 0,
              "monthlyOpenedCases": 0,
              "monthlyClosedCases": 0,
              "totalNoneAreaEvents": 0,
              "totalCheckedAreas": 0,
              "eventsByCategories_count_weapons": 0,
              "eventsByCategories_count_explosive_device": 0,
              "eventsByCategories_count_fireworks": 0,
              "eventsByCategories_count_query": 0}

    for case in Case.objects.all():
        if case.helping == 'לא':
            count += 1
            case_list.append(case)

    for case in case_list:
        if case.status == 'פתוח':
            result["totalOpenCases"] += 1

    result["monthlyClosedCases"] = len(filterDate(case_list, dates,
                                                  date_format='%d-%m-%Y', filter_by_status_closed_date=True))

    case_list = filterDate(case_list, dates, date_format='%d-%m-%Y')
    result["monthlyOpenedCases"] = len(case_list)
    for case in case_list:
        if case.received_or_go == 'קבלת אירוע':
            result["totalNoneAreaEvents"] += 1
    #

    for case in case_list:
        if case.event_characteristic == 'weapons':
            result["eventsByCategories_count_weapons"] += 1
        if case.event_characteristic == 'explosive_device':
            result["eventsByCategories_count_explosive_device"] += 1
        if case.event_characteristic == 'fireworks':
            result["eventsByCategories_count_fireworks"] += 1
        if case.event_characteristic == 'query':
            result["eventsByCategories_count_query"] += 1
    result["totalCheckedAreas"] = result["monthlyOpenedCases"] - result["totalNoneAreaEvents"]
    if get_dict:
        return result
    return JsonResponse(result, safe=False)


# The function return yearly summery(by dates)
def yearly_sum(msg):
    year = msg[-4:]
    yearly_result = monthly_sum({'min_date': ('01-01-' + year), 'max_date': ('31-12-' + year)}, get_dict=True)
    yearly_result_list = []
    index = 0
    for key in yearly_result.keys():
        if index == 0:
            index += 1
        if index == 1:
            yearly_result_list.append(0)
            index += 1
        yearly_result_list.append(yearly_result[key])
    yearly_result_list[0] = yearly_result_list[1]  # TODO
    return JsonResponse(yearly_result_list, safe=False)


# The function get the request from the frontend and ask from yearly_sum\monthly_sum the data by dates it gets from the request
@csrf_exempt
def general_sum(request):
    msg = request.path
    data_list = []
    new_msg = list(msg.split('/'))
    dates = new_msg[len(new_msg) - 1]
    if 'month' in msg:
        splited_msg = list(dates.split('|'))
        dates_data = {'min_date': splited_msg[0], 'max_date': splited_msg[1]}
        data_list = monthly_sum(dates_data)
    elif 'year' in msg:
        data_list = yearly_sum(dates)

    return data_list


# The function return list of cases that each of them has all of the search values that fuction gets
def search_tags(cases, field, data):
    data_values = data.split(",")
    res = []
    for case in cases:
        all_in_case = True
        for data_value in data_values:
            search_value = {"weapon_name": case.weapon_name,
                            "explosive_device_means": case.explosive_device_means,
                            "explosive_device_operating_system": case.explosive_device_operating_system,
                            "explosive_device_spray": case.explosive_device_spray,
                            "explosive_device_camouflage": case.explosive_device_camouflage}
            if data_value not in search_value[field]:
                all_in_case = False
                break
        if all_in_case:
            res.append(case)
    return res


# The function filtering cases by the request data
@csrf_exempt
def queryHandler(request):

    query_data = JSONParser().parse(request)
    create_default_values(query_data, CaseSerializer, default_value="")
    cases = Case.objects.all()
    if "" != query_data['internal_number']:
        cases = cases.filter(internal_number=query_data['internal_number'])
    if "" != query_data['received_or_go']:
        cases = cases.filter(received_or_go=query_data['received_or_go'])
    if "" != query_data['lab_name']:
        cases = cases.filter(lab_name=query_data['lab_name'])
    if "" != query_data['event_characteristic']:
        cases = cases.filter(event_characteristic=query_data['event_characteristic'])
    if "" != query_data['event_date']:
        cases = cases.filter(event_date=query_data['event_date'])
    if "" != query_data['received_date']:
        cases = cases.filter(received_date=query_data['received_date'])
    if "" != query_data['event_type']:
        cases = cases.filter(event_type=query_data['event_type'])
    if "" != query_data['pele_number']:
        cases = cases.filter(pele_number=query_data['pele_number'])
    if "" != query_data['district']:
        cases = cases.filter(district=query_data['district'])
    if "" != query_data['investigating_unit']:
        cases = cases.filter(investigating_unit=query_data['investigating_unit'])
    if "" != query_data['explosion_or_disarm']:
        cases = cases.filter(explosion_or_disarm=query_data['explosion_or_disarm'])
    if "" != query_data['reference_number']:
        cases = cases.filter(reference_number=query_data['reference_number'])
    if "" != query_data['status']:
        cases = cases.filter(status=query_data['status'])
    if "" != query_data['event_location']:
        cases = cases.filter(event_location=query_data['event_location'])
    if "" != query_data['event_description']:
        cases = cases.filter(event_description=query_data['event_description'])
    if "" != query_data['sender_name']:
        cases = cases.filter(sender_name=query_data['sender_name'])
    if "" != query_data['weapon_name']:
        cases = search_tags(cases, "weapon_name",
                            query_data['weapon_name'])  # cases.filter(weapon_name=query_data['weapon_name'])
    if "" != query_data['explosive_device_material']:
        cases = cases.filter(explosive_device_material=query_data['explosive_device_material'])
    if "" != query_data['explosive_device_means']:
        cases = search_tags(cases, "explosive_device_means", query_data['explosive_device_means'])
        # cases = cases.filter(explosive_device_means=query_data['explosive_device_means'])
    if "" != query_data['weapon_options']:
        cases = cases.filter(weapon_options=query_data['weapon_options'])
    if "" != query_data['explosive_device_operating_system']:
        cases = search_tags(cases, "explosive_device_operating_system", query_data['explosive_device_operating_system'])
        # cases = cases.filter(explosive_device_operating_system=query_data['explosive_device_operating_system'])
    if "" != query_data['weapon_mark']:
        cases = cases.filter(weapon_mark=query_data['weapon_mark'])
    if "" != query_data['explosive_device_spray']:
        cases = search_tags(cases, "explosive_device_spray", query_data['explosive_device_spray'])
        # cases = cases.filter(explosive_device_spray=query_data['explosive_device_spray'])
    if "" != query_data['weapon_color']:
        cases = cases.filter(weapon_color=query_data['weapon_color'])
    if "" != query_data['explosive_device_camouflage']:
        cases = search_tags(cases, "explosive_device_camouflage", query_data['explosive_device_camouflage'])
        # cases = cases.filter(explosive_device_camouflage=query_data['explosive_device_camouflage'])
    if "" != query_data['weapon_additional_characteristics']:
        cases = cases.filter(weapon_additional_characteristics=query_data['weapon_additional_characteristics'])
    cases = filterDate(cases, query_data)
    cases_serializer = CaseSerializer(cases, many=True)
    return JsonResponse(cases_serializer.data, safe=False)


# The function add\return\delete\edit the case data in the database by the type of the request:put,delete,get,post
@csrf_exempt
def caseApi(request, case_name1="", case_name2=""):
    if request.method == 'GET':
        cases = Case.objects.all()
        cases.annotate(index=Value(''))
        for row_num, case in enumerate(cases):
            case.index = row_num

        cases_serializer = CaseSerializerI(cases, many=True)
        return JsonResponse(cases_serializer.data, safe=False)

    elif request.method == 'POST':
        case_data = JSONParser().parse(request)
        create_default_values(case_data, CaseSerializer)
        if case_data['internal_number'] == "default":
            case_data["internal_number"] = idApi('case')

        department_serializer = CaseSerializer(data=case_data)
        if department_serializer.is_valid():
            department_serializer.save()
            return JsonResponse(str(case_data["internal_number"]), safe=False)
        else:
            print("error case api post", department_serializer.errors)
        return JsonResponse("Failed to Addd.", safe=False)

    elif request.method == 'PUT':
        department_data = JSONParser().parse(request)
        create_default_values(department_data, CaseSerializer)
        old_department = Case.objects.get(internal_number=department_data['internal_number'])
        if old_department.status == 'פתוח' and (
                department_data["status"] == 'סגור ללא חווד' or department_data["status"] == 'סגור חווד'):
            today = date.today()
            department_data["status_closed_date"] = today.strftime("%d-%m-%Y")
        department_serializer = CaseSerializer(old_department, data=department_data)
        if department_serializer.is_valid():
            department_serializer.save()
            return JsonResponse("Updated Successfully!!", safe=False)
        else:
            print("error case api put", department_serializer.errors)
        return JsonResponse("Failed to Update.", safe=False)

    elif request.method == 'DELETE':
        old_department = Case.objects.get(internal_number=case_name)
        old_department.delete()
        return JsonResponse("Deleted Succeffully!!", safe=False)


# write an exhibit into xlsx file
def WriteToExcelExb(exhibit_data):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet_s = workbook.add_worksheet("Exhibits")
    header = workbook.add_format({
        'bg_color': '#F7F7F7',
        'color': 'black',
        'align': 'center',
        'valign': 'top',
        'border': 1
    })
    # create collum names
    worksheet_s.write(0, 0, ugettext("מס פנימי"), header)
    worksheet_s.write(0, 1, ugettext("מס מוצג"), header)
    worksheet_s.write(0, 2, ugettext("מיקום"), header)
    worksheet_s.write(0, 3, ugettext("תיאור"), header)
    worksheet_s.write(0, 4, ugettext("כמות"), header)
    worksheet_s.write(0, 5, ugettext("ייעוד"), header)
    worksheet_s.write(0, 6, ugettext('חנ"פ'), header)
    worksheet_s.write(0, 7, ugettext('משקל חנ"פ'), header)
    worksheet_s.write(0, 8, ugettext("אקוויולנט לTNT"), header)
    worksheet_s.write(0, 9, ugettext("תאריך הכנסה"), header)
    worksheet_s.write(0, 10, ugettext("תאריך טיפול"), header)
    worksheet_s.write(0, 11, ugettext("שם החוקר"), header)
    worksheet_s.write(0, 12, ugettext("מעבדה"), header)
    worksheet_s.write(0, 13, ugettext("תוצאות הבדיקה"), header)

    for idx, data in enumerate(exhibit_data):
        row = 1 + idx
        worksheet_s.write_string(row, 0, data['internal_number'])
        worksheet_s.write_string(row, 1, data['exhibit_number'])
        worksheet_s.write_string(row, 2, data['location'])
        worksheet_s.write_string(row, 3, data['description'])
        worksheet_s.write_string(row, 4, data['amount'])
        worksheet_s.write_string(row, 5, data['destination'])
        worksheet_s.write_string(row, 6, data['explosive'])
        worksheet_s.write_string(row, 7, data['explosive_weight'])
        worksheet_s.write_string(row, 8, data['tnt_equivalent'])
        worksheet_s.write_string(row, 9, data['received_date'])
        worksheet_s.write_string(row, 10, data['handle_date'])
        worksheet_s.write_string(row, 11, data['investigator_name'])
        worksheet_s.write_string(row, 12, data['lab_name'])
        worksheet_s.write_string(row, 13, data['result'])
    workbook.close()
    xlsx_data = output.getvalue()
    # xlsx_data contains the Excel file
    return xlsx_data


# download the exhibit data as a xlsx file
@csrf_exempt
def exhibitDwnld(request):
    response = HttpResponse(content_type='application/vnd.ms-excel')  # set Http response content type
    response['Content-Disposition'] = 'attachment; filename=Exhibit_Report.xlsx'  # set attachment type
    xlsx_data = WriteToExcelExb(Exhibits.objects.values())  # generate excel file
    response.write(xlsx_data)  # add file as attachment
    return response


# write the case data into xlsx file
def WriteToExcelCase(exhibit_data):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet_s = workbook.add_worksheet("Cases")
    header = workbook.add_format({
        'bg_color': '#F7F7F7',
        'color': 'black',
        'align': 'center',
        'valign': 'top',
        'border': 1
    })
    # create collum names
    worksheet_s.write(0, 0, ugettext("מס פנימי"), header)
    worksheet_s.write(0, 1, ugettext("יציאה\קבלה"), header)
    worksheet_s.write(0, 2, ugettext("מעבדה"), header)
    worksheet_s.write(0, 3, ugettext("מאפיין אירוע"), header)
    worksheet_s.write(0, 4, ugettext("תאריך האירוע"), header)
    worksheet_s.write(0, 5, ugettext("תאריך קבלה"), header)
    worksheet_s.write(0, 6, ugettext("סוג האירוע"), header)
    worksheet_s.write(0, 7, ugettext("מס פלא"), header)
    worksheet_s.write(0, 8, ugettext("מחוז"), header)
    worksheet_s.write(0, 9, ugettext("יח חוקרת"), header)
    worksheet_s.write(0, 10, ugettext("פיצוץ/נטרול"), header)
    worksheet_s.write(0, 11, ugettext("סימוכין"), header)
    worksheet_s.write(0, 12, ugettext("סטטוס"), header)
    worksheet_s.write(0, 13, ugettext("מקום אירוע"), header)
    worksheet_s.write(0, 14, ugettext("תיאור אירוע"), header)
    worksheet_s.write(0, 15, ugettext("שם המומחה"), header)
    worksheet_s.write(0, 16, ugettext("weapon_name"), header)
    worksheet_s.write(0, 17, ugettext("explosive_device_material"), header)
    worksheet_s.write(0, 18, ugettext("explosive_device_means"), header)
    worksheet_s.write(0, 19, ugettext("weapon_options"), header)
    worksheet_s.write(0, 20, ugettext("explosive_device_operating_system"), header)
    worksheet_s.write(0, 21, ugettext("weapon_mark"), header)
    worksheet_s.write(0, 22, ugettext("explosive_device_spray"), header)
    worksheet_s.write(0, 23, ugettext("weapon_color"), header)
    worksheet_s.write(0, 24, ugettext("explosive_device_camouflage"), header)
    worksheet_s.write(0, 25, ugettext("weapon_additional_characteristics"), header)

    # put data in table
    for idx, data in enumerate(exhibit_data):
        row = 1 + idx
        worksheet_s.write_string(row, 0, data['internal_number'])
        worksheet_s.write_string(row, 1, data['received_or_go'])
        worksheet_s.write_string(row, 2, data['lab_name'])
        worksheet_s.write_string(row, 3, data['event_characteristic'])
        worksheet_s.write_string(row, 4, data['event_date'])
        worksheet_s.write_string(row, 5, data['received_date'])
        worksheet_s.write_string(row, 6, data['event_type'])
        worksheet_s.write_string(row, 7, data['pele_number'])
        worksheet_s.write_string(row, 8, data['district'])
        worksheet_s.write_string(row, 9, data['investigating_unit'])
        worksheet_s.write_string(row, 10, data['explosion_or_disarm'])
        worksheet_s.write_string(row, 11, data['reference_number'])
        worksheet_s.write_string(row, 12, data['status'])
        worksheet_s.write_string(row, 13, data['event_location'])
        worksheet_s.write_string(row, 14, data['event_description'])
        worksheet_s.write_string(row, 15, data['sender_name'])
        worksheet_s.write_string(row, 16, data['weapon_name'])
        worksheet_s.write_string(row, 17, data['explosive_device_material'])
        worksheet_s.write_string(row, 18, data['explosive_device_means'])
        worksheet_s.write_string(row, 19, data['weapon_options'])
        worksheet_s.write_string(row, 20, data['explosive_device_operating_system'])
        worksheet_s.write_string(row, 21, data['weapon_mark'])
        worksheet_s.write_string(row, 22, data['explosive_device_spray'])
        worksheet_s.write_string(row, 23, data['weapon_color'])
        worksheet_s.write_string(row, 24, data['explosive_device_camouflage'])
        worksheet_s.write_string(row, 25, data['weapon_additional_characteristics'])

    workbook.close()
    xlsx_data = output.getvalue()
    # xlsx_data contains the Excel file
    return xlsx_data


# download the case data as a xlsx file
@csrf_exempt
def caseDwnld(request):
    response = HttpResponse(content_type='application/vnd.ms-excel')  # set Http response content type
    response['Content-Disposition'] = 'attachment; filename=Case_Report.xlsx'  # set attachment type
    xlsx_data = WriteToExcelCase(Case.objects.values())  # generate excel file
    response.write(xlsx_data)  # add file as attachment
    return response


# given a case internal number, returns all exhibits related to it
# internal number should be sent as a Json param 'internal_number' : <value>
@csrf_exempt
def exhibitQuery(request, internal_number1="", internal_number2=""):
    exhibits = Exhibits.objects.all()
    internal_number = internal_number1 + "." + internal_number2
    exhibits = exhibits.filter(internal_number=internal_number)
    exhibits_serializer = ExhibitsSerializer(exhibits, many=True)
    return JsonResponse(exhibits_serializer.data, safe=False)


# The function add\return\delete\edit the exhibit data in the database by the type of the request:put,delete,get,post
@csrf_exempt
def exhibitsApi(request, exhibit_number=""):
    if request.method == 'GET':
        exhibit = Exhibits.objects.all()
        exhibit.annotate(index=Value(''))
        for row_num, exh in enumerate(exhibit):
            exh.index = row_num
        exhibits_serializer = ExhibitsSerializerI(exhibit, many=True)
        return JsonResponse(exhibits_serializer.data, safe=False)

    elif request.method == 'POST':

        exhibit_data = JSONParser().parse(request)
        exhibit_data["exhibit_number"] = idApi('exhibit', internal_number=exhibit_data["internal_number"])
        create_default_values(exhibit_data, ExhibitsSerializer)
        exhibits_serializer = ExhibitsSerializer(data=exhibit_data)
        if exhibits_serializer.is_valid():
            exhibits_serializer.save()
            return JsonResponse(str(exhibit_data["exhibit_number"]), safe=False)
        else:
            print("error in exhibits post", exhibits_serializer.errors)
        return JsonResponse("Failed to Add.", safe=False)

    elif request.method == 'PUT':
        exhibit_data = JSONParser().parse(request)
        create_default_values(exhibit_data, ExhibitsSerializer)
        exhibit = Exhibits.objects.get(internal_number=exhibit_data["internal_number"],
                                       exhibit_number=exhibit_data['exhibit_number'])
        exhibits_serializer = ExhibitsSerializer(exhibit, data=exhibit_data)
        if exhibits_serializer.is_valid():
            exhibits_serializer.save()
            return JsonResponse("Updated Successfully!!", safe=False)
        return JsonResponse("Failed to Update.", safe=False)

    elif request.method == 'DELETE':
        department = Case.objects.get(exhibit_number=exhibit_number)
        department.delete()
        return JsonResponse("Deleted Succeffully!!", safe=False)


# generate id for every new case\exhibit\sample(gives new id number for every case\exhibit\sample)
def idApi(type, internal_number=None, transferred_to_lab=None):
    id = ''
    if type == "exhibit":
        # get the last exhibit number +1
        exhibit = Exhibits.objects.all().filter(internal_number=internal_number).order_by('-exhibit_number')
        if len(exhibit) == 0:
            id = "1"
            return id
        else:
            id = int(max([float(e.exhibit_number) for e in exhibit]) + 1)
            return id
    elif type == "case":
        if Case.objects.count() == 0:
            year = date.today().year
            id = "1." + str(year)
            return id
        else:
            cases = Case.objects.all()
            year = date.today().year
            cases_current_year = []
            for case in cases:
                if case.internal_number.endswith("." + str(year)):
                    cases_current_year.append(case)
            if len(cases_current_year) == 0:
                id = "1." + str(year)
            # TODO take year into consideration
            else:
                id = str(int(max([float(c.internal_number[:c.internal_number.find(".")]) for c in
                                  cases_current_year]) + 1)) + "." + str(year)
            return id
    elif type == "samples":
        samples = Samples.objects.all().filter(internal_number=internal_number,
                                               transferred_to_lab=transferred_to_lab).order_by('-sample_id')
        if len(samples) == 0:
            id = "1"
            return id
        else:
            id = int(max([float(s.sample_id) for s in samples]) + 1)
            return id


# by given a case and an exhibit internal number, returns all samples related to it
@csrf_exempt
def sampleQuery(request):
    internal_number, exhibit_number = request.path.split("/")[-1].split("_")
    samples = Samples.objects.all()
    samples = samples.filter(internal_number=internal_number, exhibit_number=exhibit_number)
    samples_serializer = SamplesSerializer(samples, many=True)
    return JsonResponse(samples_serializer.data, safe=False)


# The function add\return\delete\edit the sample data in the database by the type of the request:put,delete,get,post
@csrf_exempt
def samplesApi(request, sample_id=""):
    if request.method == 'GET':
        samples_value = Samples.objects.all()
        samples_serializer = SamplesSerializer(samples_value, many=True)
        return JsonResponse(samples_serializer.data, safe=False)
    elif request.method == 'POST':
        samples_data = JSONParser().parse(request)
        samples_data["sample_id"] = idApi('samples', internal_number=samples_data["internal_number"],
                                          transferred_to_lab=samples_data["transferred_to_lab"])

        create_default_values(samples_data, SamplesSerializer)
        department_serializer = SamplesSerializer(data=samples_data)
        if department_serializer.is_valid():
            department_serializer.save()
            return JsonResponse(str(samples_data["sample_id"]), safe=False)
        else:
            print("error in samples post", department_serializer.errors)
        return JsonResponse("Failed to Add.", safe=False)

    elif request.method == 'PUT':
        department_data = JSONParser().parse(request)
        create_default_values(department_data, SamplesSerializer)
        department = Samples.objects.get(sample_id=department_data['sample_id'],
                                         exhibit_number=department_data['exhibit_number'],
                                         internal_number=department_data['internal_number'],
                                         transferred_to_lab=department_data['transferred_to_lab'])
        department_serializer = SamplesSerializer(department, data=department_data)
        if department_serializer.is_valid():
            department_serializer.save()
            return JsonResponse("Updated Successfully!!", safe=False)
        return JsonResponse("Failed to Update.", safe=False)

    elif request.method == 'DELETE':
        department = Samples.objects.get(SampleName=sample_id)
        department.delete()
        return JsonResponse("Deleted Succeffully!!", safe=False)


"""
    return list of all samples attributed to a case
param:
    internal_num - id of case
"""


def convert_date_format(original_date):
    return datetime.strptime(original_date, '%Y-%m-%dT%H:%M:%S.%f%z').strftime("%d/%m/%Y")


def getSampleList(internal_number, name, transferred_to_lab):
    samples = Samples.objects.filter(internal_number=internal_number, transferred_to_lab=transferred_to_lab).values()
    case = Case.objects.get(internal_number=internal_number)
    list = ""
    for index, sample in enumerate(samples):
        list += str(sample["sample_id"]) + ".  " + sample['what_sampled'] + " ממוצג מס' " + str(
            sample['exhibit_number']) \
                + ' בדוח התפיסה הוכנסו לשקית צלף שסומנה "' + str(sample['packaging']) \
                + '" והוכנסה לשקית מאובטחת לשימוש חד פעמי שמספרה ' + sample[
                    "bag_num"] + ' וסומנה "' + convert_date_format(sample[
                                                                       "date"]) + "\" מע' חבלה " \
                + case.lab_name + " " + "מס'" + " "
        list += case.pele_number if case.pele_number != "default" else sample["reference"]
        list += " " + "ר.ז "
        try:
            list += str(name.split(" ")[0][0]) + "." + str(name.split(" ")[1][0]) + '\n'
        except:  # in case only first name is provided
            list += str(name.split(" ")[0][0]) + '\n'
    return list


# download a docx file by the request data
@csrf_exempt
def downloadFile(request):
    if request.method == 'GET':
        docx_data = request.GET.dict()
        docx_data['date_created'] = date.today().strftime("%d/%m/%Y")
        docx_data['exhibit_description'] = getSampleList(docx_data['internal_number'], docx_data["name"],
                                                         docx_data["transferred_to_lab"])
        filtered = Case.objects.filter(internal_number=docx_data['internal_number']).values()[0]
        docx_data['investigating_unit'] = filtered['investigating_unit']
        # to_update = filtered.values("reference_type", "reference_number", "event_description")
        # docx_data.update() # TODO update
        file = generate_docx(docx_data)  # create file binary stream
        return FileResponse(file, as_attachment=True, filename='temp.docx')  # create return resp with file
    return Http404("Not Get Request")


# generate new id by new request of new case\exhibit\sample
@csrf_exempt
def generate_id(request):
    return JsonResponse(idApi("case"), safe=False)
