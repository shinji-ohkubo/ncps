


from google.colab import drive
drive.mount('/content/drive')
def inf(msg, style, wdth): inf = widgets.Button(description=msg, disabled=True, button_style=style, layout=widgets.Layout(min_width=wdth));display(inf)

!pip install colab_ssh --upgrade
from colab_ssh import launch_ssh_cloudflared, init_git_cloudflared
launch_ssh_cloudflared(password="nishikasai_8213402")


⚙️ Client machine configurationRequired
Don't worry, you only have to do this once per client machine.

Download Cloudflared (Argo Tunnel), then copy the absolute path of the cloudflare binary
Now, you have to append the following to your SSH config file (usually under ~/.ssh/config), and make sure you replace the placeholder with the path you copied in Step 1:
CopyHost *.trycloudflare.com
	HostName %h
	User root
	Port 22
	ProxyCommand <PUT_THE_ABSOLUTE_CLOUDFLARE_PATH_HERE> access ssh --hostname %h
	
SSH Terminal
To connect using your terminal, type this command:

Copyssh brook-ago-aged-reports.trycloudflare.com
VSCode Remote SSH
You can also connect with VSCode Remote SSH (Ctrl+Shift+P and type "Connect to Host..."). Then, paste the following hostname in the opened command palette:

Copybrook-ago-aged-reports.trycloudflare.com
