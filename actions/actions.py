from time import strftime
from typing import Any, Text, Dict, List
#
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
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


class ActionTerminarTarea(Action):

    def name(self) -> Text:
        return "action_terminar_tarea"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

            tasks = obtener_datos_arch("tasks.json")
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
                    tasks[taskId]["finished_on"] = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                    guardar_datos_arch("tasks.json", tasks)
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
            agilebotId = tracker.get_slot("agilebot")
            if agilebotId is None :
              msg = "Antes de poder ayudarte necesito que me confirmes tu nombre por favor!"
              dispatcher.utter_message(text=msg)
              return[]
            # ahora solo esta asignandole la primera tarea que encuentra, despues habria que buscar aptitudes. se podria hacer un metodo que tambien sirva al momento de pedir sugerencias.
            for taskName in tasks.keys(): 
              task = tasks[taskName]
              if task["status"] == "toDo":
                tasks[taskName]["assigned_to"].append(str(agilebotId))
                tasks[taskName]["status"] = "inProgress"
                tasks[taskName]["assigned_on"].append(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
                guardar_datos_arch("tasks.json", tasks)
                msg = "Bueno, te asigne la tarea {}, que es {}".format(taskName,task["description"])
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
            task = tracker.get_slot("task")
            agilebotId = tracker.get_slot("otherAgilebot")
            # ahora solo esta asignandole la primera tarea que encuentra, despues habria que buscar aptitudes. se podria hacer un metodo que tambien sirva al momento de pedir sugerencias.
            if agilebotId not in tasks[task]["assigned_to"]:
              tasks[task]["assigned_to"].append(str(agilebotId))
              tasks[task]["assigned_on"].append(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))

            tasks[task]["status"] = "inProgress"
            
            guardar_datos_arch("tasks.json", tasks)
            msg = "Bueno, ahi le asigne la tarea {} a {}, que es {}".format(task, agilebotId, tasks[task]["description"])
            dispatcher.utter_message(text=msg)
            return[]