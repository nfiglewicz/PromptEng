# Git Collaboration Training: Competing Teams

Welcome to the Git Collaboration training! In this session, your team will be working on a shared project using Git, collaborating by pushing and pulling code to a "central" repository hosted by one of your teammates.

---

## **Part 1: Instructions for the "Team Git Server" Member**

You are responsible for setting up and hosting your team's central Git repository. Your teammates will connect to your computer to share code.

**Prerequisites:**

* Your team's `group_task_skeleton.zip` file (provided by the trainer).
* Git installed on your computer.

**Steps:**

1.  **Find Your Computer's IP Address:**
    * This is how your teammates will connect to your Git server.
    * **Windows:** Open Command Prompt (`cmd`) and type `ipconfig`. Look for "IPv4 Address" (e.g., `192.168.1.105`).
    * **Linux/macOS:** Open Terminal and type `ifconfig` or `ip addr`. Look for the IP address associated with your main network interface (e.g., `eth0`, `wlan0`, `en0`).
    
2.  **Prepare Your Team's Initial Project:**
    * Unzip the `group_task_skeleton.zip` file to a convenient location on your computer.
    * Open Git Bash (Windows) or your terminal (Linux/macOS) and navigate into this unzipped directory.
    * Initialize a local Git repository and commit the initial code (if it's not already a Git repo):
       ```bash
       git init
       git add .
       git commit -m "Initial project setup for our team"
       ```

3.  **Create a Bare Repository for the Git Daemon:**
    * Move up one directory from your project folder:
        ```bash
        cd ..
        ```
    * Create a new directory that will serve as the **"bare" central repository** for your team. This is where your teammates will push and pull code. It's called "bare" because it doesn't contain a working copy of the files.
        ```bash
        mkdir team_repo.git
        cd team_repo.git
        git init --bare
        ```
    * Push your initial project (from Step 2) into this bare repository:
        ```bash
        # Go back to your initial project directory
        cd ..
        cd your_unzipped_project_folder

        # Add the bare repository as a remote
        git remote add team_server_repo ../team_repo.git

        # Push your initial code to the bare repository's 'main' branch
        git push team_server_repo main
        ```
    * Configure the bare repository to allow pushes from your teammates:
        ```bash
        # Go back to the bare repository
        cd ../team_repo.git

        git config core.sharedrepository true
        ```

4.  **Start the Git Daemon:**
    * Navigate back to the **parent directory** where `team_repo.git` is located.
    ```bash
        # Go back to the parent directory of the team_repo.git.
        cd ..
    ```
    * Run the Git Daemon. This command needs to **stay running** for the entire duration of the training.
        * **Your computer must remain on and connected to the network** for your teammates to access the repository!
        ```bash
        git daemon --base-path=. --export-all --enable=receive-pack
        ```
        * `--base-path=.`: Tells the daemon to serve repositories from the current directory.
        * `--export-all`: Makes all repositories in the `base-path` available.
        * `--enable=receive-pack`: **Crucial!** This allows your teammates to `git push` to your repository.
---

## **Part 2: Instructions for All Other Team Members**

You will clone your team's private central repository, work on your tasks, and push your changes.

**Prerequisites:**

* Git installed on your computer.
* The IP address of your "Team Git Server" member's computer (they will provide this to you).

**Steps:**

1.  **Clone Your Team's Repository:**
    * Open Git Bash (Windows) or your terminal (Linux/macOS).
    * Navigate to where you want to store your project on your computer.
    * Replace `YOUR_TEAM_SERVER_IP` with the actual IP address provided by your "Team Git Server" member.
        ```bash
        git clone git://YOUR_TEAM_SERVER_IP/team_repo.git
        ```
    * You will now have a `team_repo` folder on your computer containing your team's project code.
    * Navigate into the cloned repository and start working with git as usual.
---

Good luck, and happy coding!