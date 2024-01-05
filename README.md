  # HostWatcher
  
  HostWatcher is a program for monitoring the availability of hosts on the network. It allows you to monitor the status of various nodes and provides a convenient interface for visualizing the results.
  
  ## Installation
  
  To install HostWatcher, you need to install the rich library. You can do this by running the following command:
  
  ```Bash
  
  pip install rich
  ```
  
  ## Usage
  
  After installing the rich library, you can run HostWatcher using the command:
  
  ```Bash
  
  python hostwatcher.py
  ```
  
  By default, the program will use the config.json file to configure visualization styles and specify the list of hosts to monitor. The config.json file contains a list of 50 test hosts by default, but you can customize this file according to your preferences.
  
  ## Visualization using the rich library
  
  HostWatcher uses the rich library for visualization of results. Thanks to rich, you can customize output styles, colors, and text formatting to create a convenient and informative interface.
  
  ## Example config.json file
  
```JSON
  {
    "hosts": [ "google.com" ],
    "rich": {
        "console": {
            "console_color_system": "auto",
            "console_style": "bold green"
        },
        "table": {
            "status_column_width": 20,
            "success_char": "▅",
            "failed_char": "▁",
            "loss_warning": 50
        }
    }
}
```
  
  
  ## License
  
  This project is licensed under the MIT License - see the LICENSE file for details.
