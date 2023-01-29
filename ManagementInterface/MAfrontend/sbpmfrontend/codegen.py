import os.path
from zipfile import ZipFile

from lxml import etree
from owlready2 import *


class iso8601Timedelta():
    def __init__(self, value) -> None:
        self.value = value


def iso8601_get_isosplit(s, split):
    # Taken and possibly modified from https://stackoverflow.com/questions/36976138/is-there-an-easy-way-to-convert-iso-8601-duration-to-timedelta
    if split in s:
        n, s = s.split(split)
    else:
        n = 0
    return n, s


def iso8601_parser(s):
    # Taken and possibly modified from https://stackoverflow.com/questions/36976138/is-there-an-easy-way-to-convert-iso-8601-duration-to-timedelta
    s = s.split('P')[-1]
    days, s = iso8601_get_isosplit(s, 'D')
    _, s = iso8601_get_isosplit(s, 'T')
    hours, s = iso8601_get_isosplit(s, 'H')
    minutes, s = iso8601_get_isosplit(s, 'M')
    seconds, s = iso8601_get_isosplit(s, 'S')
    dt = datetime.timedelta(days=float(days), hours=float(hours), minutes=float(minutes), seconds=float(seconds))
    return dt.total_seconds()


def iso8601_unparser(s):
    return ("PT0.3S")


declare_datatype(iso8601Timedelta, "http://www.w3.org/2001/XMLSchema#dayTimeDuration", iso8601_parser, iso8601_unparser)


def typeStrMapping(typeParam):
    if typeParam is str:
        return "str"
    elif typeParam is int:
        return "int"
    elif typeParam is float:
        return "float"
    elif typeParam is datetime.datetime:
        return "datetime"
    else:
        return "str"


def getMessageMapping(iri):
    mappings = list()
    root = tree.getroot()
    query = './/{http://www.w3.org/2002/07/owl#}NamedIndividual[@{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about="' + iri + "\"]"
    searchroot = root.find(query);
    if searchroot is not None:
        for i in searchroot.findall('.//{http://www.i2pm.net/standard-pass-ont#}hasDataMappingString'):
            for j in i.getchildren():
                for k in j.getchildren():
                    mappings.append((k.get('message-ref'), k.get('ref')))
    return mappings


def getDataMapping(iri):
    tmp = list()
    mappings = dict()
    mappings["read"] = list()
    mappings["write"] = list()
    root = tree.getroot()
    query = './/{http://www.w3.org/2002/07/owl#}NamedIndividual[@{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about="' + iri + "\"]"
    searchroot = root.find(query);
    for i in searchroot.findall('.//{http://www.i2pm.net/standard-pass-ont#}hasDataMappingString'):
        for j in i.getchildren():
            for k in j.getchildren():
                tmp.append((k.get('ref'), k.get('item-write'), k.get('item-read')))
    for i in tmp:
        if i[1] == "true":
            mappings["write"].append(i[0])
        mappings["read"].append(i[0])
    return mappings


def dfs(subject):
    states = list()
    valid_states = [onto.DoState, onto.SendState, onto.ReceiveState]
    for j in subject.containsBehavior[0].contains:
        if any(x in j.is_a for x in valid_states):
            states.append(j)
    return states


def sanitizeID(raw):
    return raw.replace('-', '_').replace('+', '_');


model = None
tree = None
onto = get_ontology("sbpmfrontend/standard_PASS_ont_v_1.1.0.owl")
onto.load()
abstract = get_ontology("sbpmfrontend/abstract-layered-pass-ont.owl")
abstract.load()
with onto:
    class FullySpecifiedSubject(Thing):
        def __getVariableNames(self):
            variables = dict()
            datatypes = dict()
            for j in self.hasDataDefinition:
                for k in j.is_a:
                    if type(k) == owlready2.class_construct.Restriction:
                        variables[k.property._python_name] = k.property.label[0]
                        datatypes[k.property._python_name] = typeStrMapping(k.value)
            return variables, datatypes

        def getVaribleInitAndLookupDict(self):
            vardef_string = list()
            data_lookup_dict, datatype_lookup_dict = self.__getVariableNames()
            vardef_string.append(f'\n\tdata_lookup_dict={data_lookup_dict}')
            vardef_string.append(f'\n\tdatatype_lookup_dict={datatype_lookup_dict}')
            for k in data_lookup_dict.keys():
                vardef_string.append(f'\t{k}=None')
            vardef_string.append(f'\tinstance_name=None')
            vardef_string.append(f'\tinstance_id=None')
            vardef_string.append(f'\tdirector=None')
            vardef_string.append(f'\tioactor=None')
            vardef_string.append(f'\tpendingIO=None')
            vardef_string.append(f'\tnew_actor_payload=None')
            vardef_string.append(f'\tknown_actors=dict()')
            vardef_string.append(f'\tallowed_states=list()')
            vardef_string.append(f'\ttimeout_states=dict()')
            vardef_string.append(f'\tio_id=None')
            vardef_string.append(f'\tpool=list()')
            return '\n'.join(vardef_string)

        def getPythonTimeouthandlerDefinitionString(self, offset):
            possible_states = list()
            possible_states.append(f'\n{offset}def receiveMsg_WakeupMessage(self, message, sender):'
                                   f'\n\t{offset}if message.payload in self.timeout_states:'
                                   f'\n\t\t{offset}self.send(self.myAddress, self.timeout_states.pop(message.payload, "not found")("empty"))'
                                   f'\n\t\t{offset}logging.warning("WAKEUP: Send state data success")'
                                   f'\n\t\t{offset}if self.io_id is not None:'
                                   f'\n\t\t\t{offset}self.send(self.ioactor, self.io_id)'
                                   f'\n\t\t\t{offset}self.io_id = None')
            return '\n'.join(possible_states)

        def getHandleExitRequest(self):
            possible_states = list()
            possible_states.append(
                f'\n\tdef receiveMsg_ActorExitRequest(self, message, sender):'
                f'\n\t\tself.pendingIO = None'
                f'\n\t\tlogging.warning("Actor exits normally!")'
                f'\n\t\tself.send(self.director, {{"unregister": self.instance_id, "subject_name": self.subjectName}})'
                f'\n\t\tif self.io_id is not None:'
                f'\n\t\t\tself.send(self.ioactor, self.io_id)'
                f'\n\t\t\tself.io_id = None')
            return '\n'.join(possible_states)


    class MessageSpecification(Thing):
        def __getVariableNames(self):
            variables = list()
            variables_exist = False
            for j in self.containsPayloadDescription:
                for k in j.is_a:
                    if type(k) == owlready2.class_construct.Restriction:
                        variables.append(k.property._python_name)
                        variables_exist = True
            if not variables_exist:
                variables.append("content")
            return variables

        def __getPythonClassMemberDefinitionString(self):
            lines = list()
            for i in self.__getVariableNames():
                lines.append(f"\n\t{i}=None")
            return '\n'.join(lines)

        def __getPythonClassConstructorString(self):
            variables = self.__getVariableNames()
            template = f'\n\tdef __init__(self, {",".join([x for x in variables])}):'
            for i in variables:
                template = template + f'\n\t\tself.{i} = {i}'
            return template

        def getPythonClassDefinitionString(self):
            template = f'\nclass {sanitizeID(self.hasModelComponentID[0])}:'
            template = template + self.__getPythonClassMemberDefinitionString()
            template = template + self.__getPythonClassConstructorString()
            return template


    class CommunicationTransition(Thing):
        def getPythonClassDefinitionString(self):
            return f'\nclass {sanitizeID(self.hasModelComponentID[0])}:' \
                   '\n\tdef __init__(self, content):' \
                   '\n\t\tself.content = content' \
                   '\n\tdef __str__(self):' \
                   '\n\t\treturn str(self.content)'


    class DoTransition(Thing):
        def getPythonClassDefinitionString(self):
            return f'\nclass {sanitizeID(self.hasModelComponentID[0])}:' \
                   '\n\tdef __init__(self, content):' \
                   '\n\t\tself.content = content\n' \
                   '\n\tdef __str__(self):' \
                   '\n\t\treturn str(self.content)' \
                   f'\nclass {sanitizeID(self.hasModelComponentID[0]) + "_res"}:' \
                   '\n\tdef __init__(self, content):' \
                   '\n\t\tself.content = content\n' \
                   '\n\tdef __str__(self):' \
                   '\n\t\treturn str(self.content)'


    class DayTimeTimerTransition(Thing):
        def getPythonClassDefinitionString(self):
            return f'\nclass {sanitizeID(self.hasModelComponentID[0])}:' \
                   '\n\tdef __init__(self, content):' \
                   '\n\t\tself.content = content' \
                   '\n\tdef __str__(self):' \
                   '\n\t\treturn str(self.content)'

        def getPythonFunctionDefinitionString(self, offset=""):
            possible_states = list()

            possible_states.append(
                f'\n{offset}\tself.timeout_states["{sanitizeID(self.hasModelComponentID[0])}"]=common.{sanitizeID(self.hasModelComponentID[0])}'
                f'\n{offset}\tself.allowed_states.append("{sanitizeID(self.hasTargetState[0].hasModelComponentID[0])}")'

            )
            if self.hasTransitionCondition[0].hasDayTimeDurationTimeOutTime:
                possible_states.append(
                    f'{offset}\tself.wakeupAfter(datetime.timedelta(seconds={self.hasTransitionCondition[0].hasDayTimeDurationTimeOutTime[0]}), "{sanitizeID(self.hasModelComponentID[0])}")')
            elif self.hasTransitionCondition[0].hasTimeValue:
                possible_states.append(
                    f'{offset}\tself.wakeupAfter(datetime.timedelta(seconds={iso8601_parser(self.hasTransitionCondition[0].hasTimeValue[0])}), "{sanitizeID(self.hasModelComponentID[0])}")')
            return '\n'.join(possible_states)


    class State(Thing):
        def getPythonInitialStateDefinitionString(self):
            possible_states = list()
            possible_states.append(
                f'\ndef receiveMsg_dict(self, message, sender):'
                f'\n\ttype = message.pop("type", None)'
                f'\n\tif type == "ioresponse":'
                f'\n\t\tif self.pendingIO is None:'
                f'\n\t\t\treturn'
                f'\n\t\tif self.pendingIO == ActorExitRequest:'
                f'\n\t\t\tself.send(self.myAddress, ActorExitRequest(recursive=False))'
                f'\n\t\tself.send(self.myAddress, self.pendingIO(message))'
                f'\n\t\tself.pendingIO = None'
                f'\n\t\treturn'
                f'\n\telif type == "addressbook":'
                f'\n\t\tself.known_actors = message'
                f'\n\t\treturn'
                f'\n\telif type == "ioack":'
                f'\n\t\tself.io_id = message.get("id")'
                f'\n\t\treturn'
                f'\n\telse:'
                f'\n\t\tself.instance_name = message.get("instance_name")'
                f'\n\t\tself.instance_id = message.get("instance_id")'
                f'\n\t\tself.director = message.get("director")'
                f'\n\t\tself.ioactor = message.get("ioactor")'
                f'\n\t\tself.new_actor_payload = message'
                f'\n\t\tself.send(self.director, {{"register": self.instance_id, "subject_name": self.subjectName}})'
                f'\n\t\tself.allowed_states.append("{sanitizeID(self.hasModelComponentID[0])}")')
            return '\n'.join(possible_states)


    class DoState(Thing):
        def getInitialTmpVariableBlock(self, instancetype):
            possible_states = list()
            possible_states.append(f'\tself.timeout_states.clear()')
            possible_states.append(f'\tif "{sanitizeID(self.hasModelComponentID[0])}" not in self.allowed_states:')
            possible_states.append(f'\t\treturn')
            possible_states.append(f'\telse:')
            possible_states.append(f'\t\tself.allowed_states.clear()')
            possible_states.append(f'\ttmp = dict()')
            possible_states.append(f'\ttmp["subject_id"]= self.subjectName')
            possible_states.append(f'\ttmp["model_id"]= self.modelID')
            possible_states.append(f'\ttmp["transition_type"]= "{instancetype}"')
            possible_states.append(f'\ttmp["subject_name"]= "{self.belongsTo[0].hasModelComponentLabel[0]}"')
            possible_states.append(f'\ttmp["state_id"]= "{sanitizeID(self.hasModelComponentID[0])}"')
            possible_states.append(f'\ttmp["state_label"]= "{self.hasModelComponentLabel[0]}"')
            possible_states.append(f'\ttmp["instance_name"]= self.instance_name')
            possible_states.append(f'\ttmp["instance_id"]= self.instance_id')
            for transition in self.hasOutgoingTransition:
                if type(transition) is onto.DayTimeTimerTransition:
                    possible_states.append(transition.getPythonFunctionDefinitionString())
            return '\n'.join(possible_states)

        def getSendAndReceiveBlock(self):
            possible_states = list()
            possible_states.append(
                f'\n\tself.send(self.ioactor, tmp)')
            if not self.isEndStateOf:
                possible_states.append(
                    f'\n\tself.pendingIO = common.{sanitizeID(self.hasOutgoingTransition[0].hasModelComponentID[0])}_res'
                    f'\ndef receiveMsg_{sanitizeID(self.hasOutgoingTransition[0].hasModelComponentID[0])}_res(self, message, sender):'
                    f'\n\trecv_tmp = message.content')
                if len(self.hasOutgoingTransition) > 1:
                    possible_states.append(
                        f'\n\tchoices = [{",".join(["common." + sanitizeID(str(x.hasModelComponentID[0])) for x in self.hasOutgoingTransition])}]'
                        f'\n\tchoices_userStr = [{",".join([chr(34) + str(x.hasModelComponentLabel[0] + chr(34)) for x in self.hasOutgoingTransition])}]'
                    )
                for transition in self.hasOutgoingTransition:
                    possible_states.append(
                        f'\tself.allowed_states.append("{sanitizeID(transition.hasTargetState[0].hasModelComponentID[0])}")')
            else:
                possible_states.append(
                    f'\n\tself.pendingIO = ActorExitRequest')
            return '\n'.join(possible_states)

        def getCompleteDataMappingBlock(self):
            possible_states = list()
            for i in self.hasDataMappingFunction:
                possible_states.append(f'\ttmp["write"] = dict()')
                possible_states.append(f'\ttmp["read"] = dict()')
                tmp = getDataMapping(i.iri)
                for i in tmp.get("read", []):
                    possible_states.append(
                        f'\ttmp["read"]["{i}"]={{"display_name":self.data_lookup_dict["{i}"],"value":self.{i},"datatype":self.datatype_lookup_dict["{i}"]}}')
                for i in tmp.get("write", []):
                    possible_states.append(
                        f'\ttmp["write"]["{i}"]={{"display_name":self.data_lookup_dict["{i}"],"value":self.{i},"datatype":self.datatype_lookup_dict["{i}"]}}')
                possible_states.append(self.getSendAndReceiveBlock())
                for i in tmp.get("write", []):
                    possible_states.append(
                        f'\tself.{i}=recv_tmp["{i}"]')
            if not self.hasDataMappingFunction:
                possible_states.append(
                    self.getSendAndReceiveBlock()
                )
            return '\n'.join(possible_states)

        def getPythonFunctionDefinitionString(self):
            possible_states = list()
            if self.isInitialStateOf:
                possible_states.append(self.getPythonInitialStateDefinitionString())
                possible_states.append(self.getInitialTmpVariableBlock("initial"))
                possible_states.append(self.getCompleteDataMappingBlock())
                possible_states.append(
                    f'\tself.send(self.myAddress, common.{sanitizeID(self.hasOutgoingTransition[0].hasModelComponentID[0])}("data"))')

            elif self.isEndStateOf:
                for transition in self.hasIncomingTransition:
                    possible_states.append(
                        f'\ndef receiveMsg_{sanitizeID(transition.hasModelComponentID[0])}(self, message, sender):')
                    possible_states.append(self.getInitialTmpVariableBlock("end"))
                    possible_states.append(self.getCompleteDataMappingBlock())
            else:
                if len(self.hasOutgoingTransition) > 1:
                    for incoming_transition in self.hasIncomingTransition:
                        possible_states.append(
                            f'\ndef receiveMsg_{sanitizeID(incoming_transition.hasModelComponentID[0])}(self, message, sender):'
                            f'\n\tchoices = [{",".join(["common." + sanitizeID(str(x.hasModelComponentID[0])) for x in self.hasOutgoingTransition])}]'
                            f'\n\tchoices_userStr = [{",".join([chr(34) + str(x.hasModelComponentLabel[0] + chr(34)) for x in self.hasOutgoingTransition])}]')

                        possible_states.append(self.getInitialTmpVariableBlock("multi"))
                        possible_states.append(f'\ttmp["choices"]= choices_userStr')
                        possible_states.append(self.getCompleteDataMappingBlock())
                        possible_states.append(
                            f'\n\tself.send(self.myAddress, choices[int(recv_tmp["next"])]("data"))'
                        )
                else:
                    for incoming_transition in self.hasIncomingTransition:
                        possible_states.append(
                            f'\ndef receiveMsg_{sanitizeID(incoming_transition.hasModelComponentID[0])}(self, message, sender):')
                        possible_states.append(self.getInitialTmpVariableBlock("trivial"))
                        possible_states.append(self.getCompleteDataMappingBlock())
                        possible_states.append(
                            f'\n\tself.send(self.myAddress, common.{sanitizeID(self.hasOutgoingTransition[0].hasModelComponentID[0])}("data"))'
                        )
            return '\n'.join(possible_states)


    class ReceiveState(Thing):
        def getPythonFunctionDefinitionString(self):
            possible_states = list()
            relevant_message_types = list()
            if self.isInitialStateOf:
                possible_states.append(self.getPythonInitialStateDefinitionString())
            for outgoing_transition in self.hasOutgoingTransition:
                if type(outgoing_transition) is not onto.ReceiveTransition:
                    continue
                otherActor = \
                    sanitizeID(outgoing_transition.hasTransitionCondition[0].requiresMessageSentFrom[
                                   0].hasModelComponentID[0])
                relevant_message_types.append(
                    sanitizeID(
                        outgoing_transition.hasTransitionCondition[0].requiresReceptionOfMessage[0].hasModelComponentID[
                            0]))
                possible_states.append(
                    f'\ndef receiveMsg_{sanitizeID(outgoing_transition.hasTransitionCondition[0].requiresReceptionOfMessage[0].hasModelComponentID[0])}(self, message, sender):'
                    f'\n\tif sender != self.myAddress:'
                    f'\n\t\tself.{otherActor.lower()} = sender'
                    f'\n\tif "{sanitizeID(self.hasModelComponentID[0])}" not in self.allowed_states:'
                    f'\n\t\tself.pool.append(message)'
                    f'\n\t\treturn'
                    f'\n\telse:'
                    f'\n\t\tself.allowed_states.clear()'
                    f'\n\tself.timeout_states.clear()'
                )
                for transition in self.hasOutgoingTransition:
                    possible_states.append(
                        f'\tself.allowed_states.append("{sanitizeID(transition.hasTargetState[0].hasModelComponentID[0])}")')
                data_mapping_functions = outgoing_transition.hasDataMappingFunction
                if data_mapping_functions is not None and len(data_mapping_functions) >= 1:
                    mapping = getMessageMapping(data_mapping_functions[0].iri)
                    for k in mapping:
                        possible_states.append(f'\tself.{k[1]} = message.{k[0]}')
                possible_states.append(
                    f'\tself.send(self.myAddress, common.{sanitizeID(outgoing_transition.hasModelComponentID[0])}(message))'
                )
            for incoming_transition in self.hasIncomingTransition:
                possible_states.append(
                    f'\ndef receiveMsg_{sanitizeID(incoming_transition.hasModelComponentID[0])}(self, message, sender):'
                    f'\n\tfor idx, pending_message in enumerate(self.pool):'
                    f'\n\t\tif type(pending_message) in [{",".join(["common." + x for x in relevant_message_types])}]:'
                    f'\n\t\t\tself.send(self.myAddress, pending_message)'
                    f'\n\t\t\tdel self.pool[idx]'
                )
                for outgoing_transition in self.hasOutgoingTransition:
                    if type(outgoing_transition) is onto.DayTimeTimerTransition:
                        possible_states.append(outgoing_transition.getPythonFunctionDefinitionString())
            return '\n'.join(possible_states)

        def __getPythonClassMemberDefinitionString(self):
            lines = list()
            for i in self.__getVariableNames():
                lines.append(f"\n\t{i}=None")
            return '\n'.join(lines)


    class SendState(Thing):
        def __build_newmessage(self, outgoing_transition):
            possible_states = list()
            data_mapping_functions = outgoing_transition.hasDataMappingFunction
            if data_mapping_functions is not None and len(data_mapping_functions) >= 1:
                mapping = getMessageMapping(data_mapping_functions[0].iri)
                possible_states.append(
                    f'\n\tnewmessage = common.{sanitizeID(outgoing_transition.hasTransitionCondition[0].requiresSendingOfMessage[0].hasModelComponentID[0])}'
                    f'({",".join([f"{x[0]}=self.{x[1]}" for x in mapping])})')
            else:
                possible_states.append(
                    f'\n\tnewmessage = common.{sanitizeID(outgoing_transition.hasTransitionCondition[0].requiresSendingOfMessage[0].hasModelComponentID[0])}("content")')
            return '\n'.join(possible_states)

        def __send_to_other_actor(self, otherActor, offset):
            possible_states = list()
            possible_states.append(
                f'\n{offset}if "{sanitizeID(self.hasModelComponentID[0])}" not in self.allowed_states:'
                f'\n{offset}\treturn'
                f'\n{offset}if "{otherActor}" not in self.known_actors:'
                f'\n{offset}\tif self.{otherActor.lower()} is None:'
                f'\n{offset}\t\tself.{otherActor.lower()} = self.createActor({otherActor.lower()}.{otherActor})'
                f'\n{offset}\t\tself.send(self.{otherActor.lower()}, self.new_actor_payload)'
                f'\n{offset}else:'
                f'\n{offset}\tself.{otherActor.lower()} = self.known_actors["{otherActor}"][0]'
                f'\n{offset}self.timeout_states.clear()'
                f'\n{offset}self.allowed_states.clear()'
            )
            for transition in self.hasOutgoingTransition:
                possible_states.append(
                    f'\tself.allowed_states.append("{sanitizeID(transition.hasTargetState[0].hasModelComponentID[0])}")')
            return '\n'.join(possible_states)

        def getPythonFunctionDefinitionString(self):
            possible_states = list()
            otherActor = \
                sanitizeID(self.hasOutgoingTransition[0].hasTransitionCondition[0].requiresMessageSentTo[
                               0].hasModelComponentID[0])
            if self.isInitialStateOf:
                possible_states.append(self.getPythonInitialStateDefinitionString())
                possible_states.append(self.__send_to_other_actor(otherActor, '\t\t'))
                for outgoing_transition in self.hasOutgoingTransition:
                    possible_states.append(self.__build_newmessage(outgoing_transition))
                    possible_states.append(f'\n\t\tself.send(self.{otherActor.lower()}, newmessage)'
                                           f'\n\t\tself.send(self.myAddress, common.{sanitizeID(outgoing_transition.hasModelComponentID[0])}(""))')
            elif self.isEndStateOf:
                for incoming_transition in self.hasIncomingTransition:
                    possible_states.append(
                        f'\ndef receiveMsg_{sanitizeID(incoming_transition.hasModelComponentID[0])}(self, message, sender):')
                    possible_states.append(self.__send_to_other_actor(otherActor, '\t'))
                    for outgoing_transition in self.hasOutgoingTransition:
                        possible_states.append(self.__build_newmessage(outgoing_transition))
                        possible_states.append(
                            f'\n\tself.send(self.{otherActor.lower()}, newmessage)')
                    possible_states.append(
                        f'\n\tself.send(self.myAddress, ActorExitRequest(recursive=False))')
            else:
                for incoming_transition in self.hasIncomingTransition:
                    possible_states.append(
                        f'\ndef receiveMsg_{sanitizeID(incoming_transition.hasModelComponentID[0])}(self, message, sender):')
                    possible_states.append(self.__send_to_other_actor(otherActor, '\t'))
                    for outgoing_transition in self.hasOutgoingTransition:
                        possible_states.append(self.__build_newmessage(outgoing_transition))
                        possible_states.append(
                            f'\n\tself.send(self.{otherActor.lower()}, newmessage)')
                        possible_states.append(
                            f'\n\tself.send(self.myAddress, common.{sanitizeID(outgoing_transition.hasModelComponentID[0])}(""))')
            return '\n'.join(possible_states)


def codegen(filename, modelID, zipfilename="src.zip", ):
    returnlist = list()
    global model
    model = get_ontology(filename)
    model.load()
    global tree
    tree = etree.parse(filename)
    workdir = './codegen-tmp/'
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    files_to_zip = list()
    commonpy = list()
    f = open(workdir + 'common.py', 'w')
    for i in model.search(type=onto.MessageSpecification):
        commonpy.append(i.getPythonClassDefinitionString())
    for i in model.search(type=onto.CommunicationTransition):
        commonpy.append(i.getPythonClassDefinitionString())
    for i in model.search(type=onto.DayTimeTimerTransition):
        commonpy.append(i.getPythonClassDefinitionString())
    for i in model.search(type=onto.DoTransition):
        commonpy.append(i.getPythonClassDefinitionString())
    files_to_zip.append(workdir + "common.py")
    f.writelines(commonpy)
    f.close()
    subjects = [sanitizeID(x.hasModelComponentID[0]) for x in model.search(type=onto.FullySpecifiedSubject)]
    for i in model.search(type=onto.FullySpecifiedSubject):
        file_content = list()
        f = open(workdir + f'{sanitizeID(i.hasModelComponentID[0]).lower()}.py', 'w')
        returnlist.append(
            (f'{sanitizeID(i.hasModelComponentID[0]).lower()}.{sanitizeID(i.hasModelComponentID[0])}',
             sanitizeID(i.hasModelComponentLabel[0])))
        files_to_zip.append(workdir + f'{sanitizeID(i.hasModelComponentID[0]).lower()}.py')
        states = dfs(i)
        file_content.append('from thespian.actors import *')
        file_content.append('import requests')
        file_content.append('import datetime')
        file_content.append('import common')
        file_content.append('import json')
        for g in subjects:
            if g != sanitizeID(i.hasModelComponentID[0]):
                file_content.append(f'import {g.lower()}')
            else:
                continue
        file_content.append('@requireCapability("Server")')
        file_content.append(f'class {sanitizeID(i.hasModelComponentID[0])}(ActorTypeDispatcher):')
        file_content.append(f'\tmodelID = {modelID}')
        file_content.append(f'\tsubjectName = "{sanitizeID(i.hasModelComponentID[0])}"')
        file_content.append(i.getVaribleInitAndLookupDict())
        for g in subjects:
            if g != sanitizeID(i.hasModelComponentID[0]):
                file_content.append(f'\t{g.lower()} = None')
            else:
                continue
        for j in states:
            lines = j.getPythonFunctionDefinitionString().split('\n')
            for k in lines:
                file_content.append('\t' + k)
        file_content.append('\t' + i.getHandleExitRequest())
        file_content.append(i.getPythonTimeouthandlerDefinitionString('\t'))
        f.write('\n'.join(file_content))
        f.close()
    with ZipFile(zipfilename, 'w') as myzip:
        for i in files_to_zip:
            myzip.write(i, os.path.basename(i))
        myzip.close()
    model.destroy()
    model = None
    return returnlist
