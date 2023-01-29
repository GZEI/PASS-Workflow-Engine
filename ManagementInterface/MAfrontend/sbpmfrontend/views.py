import json

from django import forms
from django.contrib import messages
from django.forms import ModelForm
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.template import loader

from .codegen import *
from .models import *
from .runner import *


def typeStrMapping(typeParam, label):
    if typeParam == "str":
        return forms.CharField(max_length=256, label=label)
    elif typeParam == "int":
        return forms.IntegerField(min_value=0, label=label)
    elif typeParam == "float":
        return forms.FloatField(min_value=0, label=label)
    elif typeParam == "datetime":
        return forms.DateTimeField(widget=forms.widgets.DateTimeInput(attrs={'type': 'date'}), label=label)
    else:
        return forms.CharField(max_length=256, label=label)


class DynamicFormUserInput(forms.Form):
    def __init__(self, *args, **kwargs):
        fields_json = kwargs.pop("fields_json")
        super().__init__(*args, **kwargs)
        form_fields = fields_json.get("write", [])
        for k in form_fields:
            self.fields[f'{k}'] = typeStrMapping(form_fields[k].get("datatype"), form_fields[k].get("display_name"))
        choice_fields = fields_json.get("choices", [])
        if choice_fields:
            choices = list()
            for count, value in enumerate(choice_fields):
                choices.append((count, value))
            print(choices)
            self.fields["next"] = forms.ChoiceField(choices=choices)


class UploadForm(forms.Form):
    file = forms.FileField()
    name = forms.CharField(max_length=128)


class ConfigureInstanceForm(forms.Form):
    name = forms.CharField(max_length=128)


class ProcessModelForm(ModelForm):
    class Meta:
        model = ProcessModel
        fields = ['name']


class ActorForm(ModelForm):
    class Meta:
        model = SbpmActor
        fields = ['is_start_actor', 'executed_by']


class IORequest:
    actor = None
    process_instance = None
    payload = None
    requestID = None

    def __init__(self, actor, process_instance, requestID, payload):
        self.actor = actor
        self.process_instance = process_instance
        self.requestID = requestID
        self.payload = payload


def index(request):
    model_list = ProcessModel.objects.all()
    template = loader.get_template("sbpmfrontend/index.html")
    pending_requests = list()
    if request.user.is_authenticated:
        pending_requests_raw = ask_pending_requests()
        for k, v in pending_requests_raw.items():
            allowed_actors = SbpmActor.objects.filter(executed_by=request.user)
            actor = SbpmActor.objects.filter(process_model_id=v.get('model_id'))
            actor = actor.get(name=v.get('subject_id').lower() + '.' + v.get('subject_id'))
            if actor in allowed_actors:
                pending_requests.append(
                    IORequest(actor, get_object_or_404(ProcessInstance, pk=v.get("instance_id")), k, v))
        current_running_instances = []
        dict_of_hashes = ask_running_actors()
        for i in dict_of_hashes.keys():
            current_running_instances.append(i)
    context = {
        'model_list': model_list,
        'pending_io_requests': pending_requests
    }
    return HttpResponse(template.render(context, request))


def handle_uploaded_process_model(f, name):
    filename = f.name
    process_model = ProcessModel.objects.create(file_name=filename, name=name)
    filepath = "media/" + str(process_model.id)
    with open(filepath, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    available_actors = list()
    zipfile_name = "media/" + str(process_model.id) + ".zip"
    for name, display_name in codegen(filepath, process_model.id, zipfilename=zipfile_name):
        available_actors.append(
            SbpmActor.objects.create(name=name, display_name=display_name, process_model=process_model))
    return HttpResponseRedirect('/sbpm/model/' + str(process_model.id) + '/')


def upload_process_model(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            return handle_uploaded_process_model(request.FILES['file'], form.cleaned_data.get('name'))
    else:
        form = UploadForm()
    return render(request, 'sbpmfrontend/upload.html', {'form': form})


def edit_process_model(request, process_model_id):
    current_instance = get_object_or_404(ProcessModel, pk=process_model_id)
    can_start = request.user.id in SbpmActor.objects.filter(process_model_id=current_instance.id).filter(
        is_start_actor=True).values_list("executed_by_id", flat=True) or request.user.is_superuser
    if request.method == 'POST':
        form = ProcessModelForm(request.POST, request.FILES, instance=current_instance)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/sbpm/")
    else:
        form = ProcessModelForm(instance=current_instance)
        start_instance_form = ConfigureInstanceForm()
    return render(request, "sbpmfrontend/edit_process_model.html", {
        "form": form,
        "model": current_instance,
        "start_instance_form": start_instance_form,
        "can_start": can_start
    })


def edit_actor(request, actor_id):
    current_instance = get_object_or_404(SbpmActor, pk=actor_id)
    if request.method == 'POST':
        form = ActorForm(request.POST, request.FILES, instance=current_instance)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect("/sbpm/model/" + str(current_instance.process_model_id) + "/")
    else:
        form = ActorForm(instance=current_instance)

    return render(request, "sbpmfrontend/edit_actor.html", {
        "form": form,
        "model": current_instance
    })


def response_user_interaction(request, iorequest_id):
    io_request = IORequest.objects.get(pk=iorequest_id)
    if io_request.served:
        return JsonResponse(json.loads(io_request.response_content))
    else:
        return HttpResponseNotFound("Not ready yet or does not exist")


def enter_data(request, iorequest_id):
    io_request = ask_pending_requests().get(iorequest_id)
    if io_request is None:
        return HttpResponseNotFound("IO Request not found")
    json_data_dict = io_request
    if request.method == 'POST':
        form = DynamicFormUserInput(request.POST, fields_json=json_data_dict)
        if form.is_valid():
            tmp = dict()
            for i in json_data_dict.get("write", []):
                tmp[i] = form.data.dict().get(i)
            for i in form.data.dict().get('next', []):
                tmp["next"] = i
            respond_pending_request({iorequest_id: tmp})
            return HttpResponseRedirect("/sbpm")
    else:
        form = DynamicFormUserInput(fields_json=json_data_dict)
    return render(request, 'sbpmfrontend/input_data.html',
                  {'form': form, 'io_read': json_data_dict.get("read"), "io_name": json_data_dict.get("state_label"),
                   "id": iorequest_id})


def load_source(request, process_model_id):
    try:
        process_model = get_object_or_404(ProcessModel, pk=process_model_id)
        filename = "media/" + str(process_model.id) + ".zip"
        start_actors = SbpmActor.objects.filter(process_model_id=process_model.id).filter(
            is_start_actor=True).values_list("name", flat=True)
        process_model.hash = loadSource(filename, start_actors)
        process_model.save()
        messages.success(request, "Success!")
    except Exception as e:
        messages.error(request, "Error, something is bad: " + str(e))
    return HttpResponseRedirect("/sbpm/model/" + str(process_model.id) + '/')


def start_instance(request, process_model_id):
    try:
        process_model = get_object_or_404(ProcessModel, pk=process_model_id)
        start_actors = SbpmActor.objects.filter(process_model_id=process_model.id).filter(
            is_start_actor=True).values_list("name", flat=True)
        instance_name = request.GET.get('name')
        process_instance = ProcessInstance.objects.create(name=instance_name, state=0, model_id=process_model.id)
        for start_actor in start_actors:
            print(start_actor)
            startSource(start_actor, process_model.hash,
                        {"instance_name": process_instance.name, "instance_id": process_instance.id})
        messages.success(request, "Success!")
    except Exception as e:
        messages.error(request, "Error, something is bad: " + str(e))
    return HttpResponseRedirect("/sbpm/model/" + str(process_model.id) + '/')


def recompile(request, process_model_id):
    process_model = ProcessModel.objects.get(pk=process_model_id)
    filepath = "media/" + str(process_model.id)
    zipfile_name = "media/" + str(process_model.id) + ".zip"
    codegen(filepath, process_model.id, zipfilename=zipfile_name)
    messages.success(request, "Success!")
    return HttpResponseRedirect('/sbpm/model/' + str(process_model.id) + '/')


def manage_running(request):
    dict_of_hashes = ask_running_actors()
    display_list = []
    for i in dict_of_hashes.keys():
        display_list.append((get_object_or_404(ProcessInstance, pk=i), dict_of_hashes[i].get("cnt")))
    return render(request, 'sbpmfrontend/manage_current_running.html',
                  {'models': display_list})
