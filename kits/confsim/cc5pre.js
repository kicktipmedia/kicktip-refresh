/* cc5 rev 5.1: runs in <head> before first paint. Marks the page as script-enabled (html.cc5js) so cc5pages.css can reserve the simulator's height while it loads (no layout jump).
   The reservation is lifted (html.cc5ok) by cc5conf.js once the simulator has rendered, or after 10 s as a fail-safe. Without JavaScript nothing is reserved and the page keeps its original content. */
(function () { var d = document.documentElement; d.classList.add("cc5js"); setTimeout(function () { d.classList.add("cc5ok"); }, 10000); })();
