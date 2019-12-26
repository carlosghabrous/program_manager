# RegFGC3 Program Manager

The RegFGC3 program manager is a service in charge of reprogramming remotely boards on 
converter controls' crates. The service checks which FW the boards are running first, and checks these data
against either a file or database, depending on options set in a configuration file. 
Since the number of potential items to be reprogrammed is large (O(1000)), it addresses them by spawning different 
threads by location. Each of these threads runs a thread pool where jobs are queued. 