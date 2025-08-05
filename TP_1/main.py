from multiprocessing import Process, Pipe, Queue
from analizador import (
    analizador_frecuencia,
    analizador_presion,
    analizador_oxigeno
)
from verificador import verificador
from generador import generador  # ahora es un proceso propio

if __name__ == "__main__":
    # Pipes: GENERADOR → ANALIZADORES
    gen2freq_parent, gen2freq_child = Pipe()
    gen2pres_parent, gen2pres_child = Pipe()
    gen2oxi_parent,  gen2oxi_child  = Pipe()

    # Queues: ANALIZADORES → VERIFICADOR
    queue_freq = Queue()
    queue_pres = Queue()
    queue_oxi  = Queue()

    # Procesos ANALIZADORES
    proc_freq = Process(target=analizador_frecuencia, args=(gen2freq_parent, queue_freq))
    proc_pres = Process(target=analizador_presion, args=(gen2pres_parent, queue_pres))
    proc_oxi  = Process(target=analizador_oxigeno,  args=(gen2oxi_parent,  queue_oxi))

    # Proceso VERIFICADOR
    proc_verif = Process(target=verificador, args=(queue_freq, queue_pres, queue_oxi))

    # Proceso GENERADOR
    proc_gen = Process(target=generador, args=(gen2freq_child, gen2pres_child, gen2oxi_child))

    # Iniciar todos los procesos
    proc_freq.start()
    proc_pres.start()
    proc_oxi.start()
    proc_verif.start()
    proc_gen.start()

    # Esperar que todos terminen
    proc_gen.join()
    proc_freq.join()
    proc_pres.join()
    proc_oxi.join()
    proc_verif.join()

    print("Sistema finalizado correctamente.")
