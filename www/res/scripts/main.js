"use strict";

window.addEventListener("DOMContentLoaded", () => {
    const status = parseInt(document.title.split(' ')[0]) || 200;

    initNav();
    initJobs();

    if (window.location.pathname.startsWith('/calendar/') && status === 200) {
        initCalendar();
    }
});

function initCalendar() {
    const main = document.getElementsByTagName("main")[0];

    const uri = window.location.pathname;
    const parts = uri.split('/');

    const subject = parts[2];
    const year = parseInt(parts[3]);
    const week = parseInt(parts[4].substr(1));

    const cal = new WeekSchedule(subject, main);
    cal.setCurrentEventCb((events) => {
        const navLive = document.getElementById("nav-live");
        const liveButtons = navLive.getElementsByClassName("live");
        for (const btn of liveButtons) btn.href = '';

        console.log(events);
        for (let i = 0, j = 0; i < events.length; i++) {
            const evt = events[i];
            if (evt.live && evt.liveUrl) {
                const btn = liveButtons[j++];
                btn.href = evt.liveUrl;
                btn.getElementsByTagName("span")[0].innerText = evt.courseShort || evt.courseNr;
            }
        }
    });
    cal.setWeek(new Week(year, week));
}

function initNav() {
    const userMenu = document.getElementById("user-menu");
    const menu = document.getElementById("nav-home").getElementsByTagName("a")[0];
    const nav = document.getElementsByTagName("nav")[0];
    //const testElem = document.getElementById("nav-search").getElementsByTagName("form")[0];
    const testElem = document.getElementById("nav-live");

    if (userMenu) {
        const navUser = userMenu.getElementsByTagName("div")[0];
        navUser.addEventListener("click", (evt) => {
            if (userMenu.classList.contains("active")) {
                userMenu.classList.remove("active");
            } else {
                userMenu.classList.add("active");
            }
        });

        const form = document.forms.logout;
        const links = userMenu.getElementsByTagName("a");
        for (const a of links) {
            if (a.href.endsWith('/account/logout')) {
                a.removeAttribute("href");
                a.addEventListener("click", (evt) => {
                    form.submit();
                });
            }
        }
    }

    menu.addEventListener("click", (evt) => {
        if (nav.classList.contains("active")) {
            nav.classList.remove("active");
            evt.preventDefault();
        } else if (window.getComputedStyle(testElem).display === 'none') {
            nav.classList.add("active");
            evt.preventDefault();
        }
    });

    window.addEventListener("click", (evt) => {
        if (userMenu && !evt.composedPath().includes(userMenu)) {
            userMenu.classList.remove("active");
        }
        if (!evt.composedPath().includes(nav)) {
            nav.classList.remove("active");
        }
    });
}

function initJobs() {
    const jobs = document.getElementsByClassName("job-viewer");
    for (const job of jobs) {
        new Job(job);
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
}