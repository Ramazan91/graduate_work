if ("Notification" in window) {
  Notification.requestPermission();

  function checkReminders() {
    const tasks = document.querySelectorAll("[data-due]");
    const now = new Date();

    tasks.forEach(task => {
      const due = new Date(task.dataset.due);
      if (!task.dataset.notified && due <= now) {
        new Notification("Напоминание", { body: task.dataset.title });
        task.dataset.notified = "true"; // чтобы не спамило
      }
    });
  }

  setInterval(checkReminders, 60000); // проверка каждую минуту
}

