from time import strftime
from typing import Any, Text, Dict, List
#
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

import json
from datetime import datetime


def obtener_datos_arch(ruta):
    a_file = open(str(ruta), "r")
    json_object = json.load(a_file)
    a_file.close()
    return json_object

def guardar_datos_arch(ruta, datos):
    a_file = open(str(ruta), "w")
    json.dump(datos, a_file)
    a_file.close()

def generateNewProfile(agilebotId) -> Dict[Text,Any]:
  return {str(agilebotId): {"habilidades":{},"assigned_tasks":[]}}

def getRecomendedTasks(skills, tasks) -> List[Text]:
  orderedSkills = {k: skills[k] for k in sorted(skills, key=skills.get, reverse=True)}
  recommended = {"high":[],"medium":[], "low":[]}
  for taskName, task in tasks.items():
    requirements = task["task_requirements"]

    # si posee todos los skills requeridos para la task
    if (all(skill in requirements for skill in orderedSkills.keys()) or all(skill in orderedSkills.keys() for skill in requirements)):
        recommended["high"].append(taskName) # lo agrega al principio porque va a ser el mejor match
    
    for req in requirements:
      if taskName not in recommended["high"]:
        if req in orderedSkills and orderedSkills[req] >= 0.5: # si posee la skill con un grado de habilidad mayor a 0.5
          if taskName in recommended["medium"]:
            recommended["medium"].remove(taskName) # si posee mas de una skill requerida (pero no todas) con grado de habilidad mayor a 0.5 pasa a alta prioridad
            recommended["high"].append(taskName)
          else:
            if taskName in recommended["low"]: # la tarea ya estaba en low por algun otro requerimiento
              recommended["low"].remove(taskName) # si posee mas de una skill requerida (pero no todas) con grado de habilidad mayor a 0.5 pasa a alta prioridad
              recommended["medium"].insert(0,taskName)
            recommended["medium"].append(taskName) # la tarea todavia no estaba en ningun lado
        else:
          if req in orderedSkills: # quiere decir que la tenia pero con grado de habilidad menor a 0.5
            if taskName in recommended["low"]: # se usa el mismo criterio para pasar de low a medium que para pasar de medium a high
              recommended["low"].remove(taskName) 
              recommended["medium"].append(taskName)
            else:
              if taskName in recommended["medium"]: # si tiene una task en medium y se descubre otro skill bajo se incrementa en una posicion en medium
                i = recommended["medium"].index(taskName)
                if i > 0: # no era el primer elemento de medium
                  recommended["medium"].insert(i-1, recommended["medium"].pop(i))
              else:
                recommended["low"].append(taskName)
      else: # la tarea estaba en high
        if req in orderedSkills and orderedSkills[req] >= 0.5: 
          i = recommended["high"].index(taskName)
          if i > 0: # no era el primer elemento de medium
            recommended["high"].insert(i-1, recommended["high"].pop(i))
  finalList = recommended["high"] + recommended["medium"] + recommended["low"]
  return finalList

def getRecommendedPeople(taskRequirements) -> List[Text]:
  profiles = obtener_datos_arch("profiles.json")
  recommended = []
  for name, data in profiles.items():
    if len(data["assigned_tasks"]) < 4 : # una persona puede tener como max 3 tareas asignadas
      if any(req in data["skills"] for req in taskRequirements): # si el perfil tiene cualquier skill relacionada
        if all(req in data["skills"] for req in taskRequirements): # si el perfil tiene TODAS las skills relacionadas
          recommended.insert(0,name) # si tiene todas se lo pone primero
        else:
          recommended.append(name) # si no tenia todas lo pone ultimo
  return recommended

def dayDifference(dateStarted, dateFinished):
  return (datetime.strptime(dateFinished, "%m/%d/%Y") - datetime.strptime(dateStarted, "%m/%d/%Y")).days

def recalculateSkillSet(task, skills, name) -> Dict[Text, Any]:
  for req in task["task_requirements"]:
    if (req in skills.keys()):
      if task["difficulty"] == "high":
        nameIndex = task["assigned_to"].index(name)
        if dayDifference(task["assigned_on"][nameIndex], task["finished_on"]) > 10:
          skills[req] += 0.2
        else:
          skills[req] += 0.4
      elif task["difficulty"] == "medium":
        nameIndex = task["assigned_to"].index(name)
        if dayDifference(task["assigned_on"][nameIndex], task["finished_on"]) > 5:
          skills[req] += 0.1
        else:
          skills[req] += 0.3
      else:
        nameIndex = task["assigned_to"].index(name)
        if dayDifference(task["assigned_on"][nameIndex], task["finished_on"]) < 3:
          skills[req] += 0.1
  return skills

class ActionTerminarTarea(Action):

    def name(self) -> Text:
        return "action_terminar_tarea"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

            tasks = obtener_datos_arch("tasks.json")
            profiles = obtener_datos_arch("profiles.json")
            taskId = tracker.get_slot("task")
            agilebotId = tracker.get_slot("agilebot")
            if agilebotId is None :
              msg = "Antes de poder ayudarte necesito que me confirmes tu nombre por favor!"
              dispatcher.utter_message(text=msg)
              return[]
            finished = tasks[taskId]


            if (finished is None):
                msg = "Parece que no tenias asignada la tarea " + str(taskId)
                dispatcher.utter_message(text=msg)
            else:
                if ( agilebotId in finished["assigned_to"]):
                  if (finished["status"] == "toDo"): 
                    msg = "Parece que no tenias asignada la tarea " + str(taskId)
                    dispatcher.utter_message(text=msg)
                  elif (finished["status"] == "done"):
                    msg = "Parece que la tarea {} ya ha sido terminada.".format(str(taskId))
                    dispatcher.utter_message(text=msg)
                  else:
                    tasks[taskId]["status"] = "done"
                    tasks[taskId]["finished_on"] = datetime.now().strftime("%m/%d/%Y")

                    for name in tasks[taskId]["assigned_to"]:
                      profiles[name]["assigned_tasks"].remove(taskId)
                      print("Old skill set ",name, " " ,profiles[name]["skills"])
                      profiles[name]["skills"] = recalculateSkillSet(tasks[taskId], profiles[name]["skills"], name)
                      print("New skill set ",name, " " ,profiles[name]["skills"])
                    guardar_datos_arch("tasks.json", tasks)
                    guardar_datos_arch("profiles.json", profiles)
                    dispatcher.utter_message("Ya di por finalizada tu tarea, si queres me podes pedir otra.")
                else:
                  msg = "Parece que no tenias asignada la tarea " + str(taskId)
                  dispatcher.utter_message(text=msg)
            return[]

class ActionAsignarTarea(Action):

    def name(self) -> Text:
        return "action_asignar_tarea"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

            tasks = obtener_datos_arch("tasks.json")
            profiles = obtener_datos_arch("profiles.json")
            agilebotId = tracker.get_slot("agilebot")
            if agilebotId is None :
              msg = "Antes de poder ayudarte necesito que me confirmes tu nombre por favor!"
              dispatcher.utter_message(text=msg)
              return[]
            
            if profiles[agilebotId] is None:
              profiles.update(generateNewProfile())

            pendingTasks = {k: v for k, v in tasks.items() if v["status"] == "toDo"}
            recommendedTasks = getRecomendedTasks( profiles[agilebotId]["skills"], pendingTasks)
            foundTask = recommendedTasks[0]

            if foundTask:
              tasks[foundTask]["assigned_to"].append(str(agilebotId))
              tasks[foundTask]["status"] = "inProgress"
              tasks[foundTask]["assigned_on"].append(datetime.now().strftime("%m/%d/%Y"))
              guardar_datos_arch("tasks.json", tasks)
              profiles[agilebotId]["assigned_tasks"].append(foundTask)
              guardar_datos_arch("profiles.json",profiles)
              msg = "Bueno, te asigne la tarea {}, que es {}".format(foundTask,tasks[foundTask]["description"])
              dispatcher.utter_message(text=msg)
              return []

            msg = "Perdon, no pude encontrar ninguna tarea para asignarte..."
            dispatcher.utter_message(text=msg)
            return[]

class ActionAsignarTareaForzada(Action):

    def name(self) -> Text:
        return "action_asignar_tarea_forzada"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

            tasks = obtener_datos_arch("tasks.json")
            profiles = obtener_datos_arch("profiles.json")

            task = tracker.get_slot("task")
            agilebotId = tracker.get_slot("otherAgilebot")

            if profiles[agilebotId] is None:
              profiles.update(generateNewProfile())

            if agilebotId not in tasks[task]["assigned_to"]:
              tasks[task]["assigned_to"].append(str(agilebotId))
              tasks[task]["assigned_on"].append(datetime.now().strftime("%m/%d/%Y"))
              profiles[agilebotId]["assigned_tasks"].append(task)
                
            tasks[task]["status"] = "inProgress"
            guardar_datos_arch("tasks.json", tasks)
            guardar_datos_arch("profiles.json",profiles)

            msg = "Bueno, ahi le asigne la tarea {} a {}, que es {}".format(task, agilebotId, tasks[task]["description"])
            dispatcher.utter_message(text=msg)
            return[SlotSet("otherAgilebot", None)]


class ActionRecomendarTarea(Action):

    def name(self) -> Text:
        return "action_recomendar_tarea"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

            tasks = obtener_datos_arch("tasks.json")
            profiles = obtener_datos_arch("profiles.json")
            agilebotId = tracker.get_slot("otherAgilebot")
            if not agilebotId:
              agilebotId = tracker.get_slot("agilebot")
            
            pendingTasks = {k: v for k, v in tasks.items() if v["status"] == "toDo"}
            recommendedTasks = getRecomendedTasks( profiles[agilebotId]["skills"], pendingTasks)
            msg = ""
            for i in range(0,3):
              if recommendedTasks:
                msg += "- {} : {} \n".format(recommendedTasks[0], pendingTasks[recommendedTasks[0]]["description"])
                recommendedTasks.pop(0)
            if msg != "":
              msg = "Las tareas que te recomiendo son:\n" + msg
              dispatcher.utter_message(text=msg)
              return[SlotSet("otherAgilebot",None)]
            else:
              dispatcher.utter_message(text="No pude encontrar ninguna tarea para recomendar.")
              return[SlotSet("otherAgilebot",None)]
            
class ActionRecomendarPersona(Action):

    def name(self) -> Text:
        return "action_recomendar_persona"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

            task = tracker.get_slot("task")
            tasks = obtener_datos_arch("tasks.json")
            if task:
              personas = getRecommendedPeople(tasks[task]["task_requirements"])
              if personas:
                msg = "Las personas que mas recomiendo para hacer la tarea {} son:\n".format(task)
                for person in personas:
                  msg += "- {}\n".format(person)
                dispatcher.utter_message(text=msg)
                return[]
              else:
                dispatcher.utter_message(text="Perdon, no pude encontrar a nadie para recomendarte.")
                return[]
            else:
              dispatcher.utter_message(text="Parece que esa tarea no existe.")
              return[]
