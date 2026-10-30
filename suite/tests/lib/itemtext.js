/* the chat panel's itemText (assets/chat.js), reproduced for tests: the wording of each scenario line on the facts card. */
module.exports = function (B) {
  const nm = (t) => B.teams[t].n;
  return function itemText(it, res, i) {
    const e = res && res.echo && res.echo[i];
    if (it.kind === 'next_win' || it.kind === 'next_loss') return nm(it.team) + (it.kind === 'next_win' ? ' wins' : ' loses') + ' next game';
    if (it.kind === 'beats') return nm(it.winner) + ' beats ' + nm(it.loser);
    if (it.kind === 'wins_out') return nm(it.team) + ' wins out';
    if (it.kind === 'loses_out') return nm(it.team) + ' loses out';
    if (it.kind === 'loses_n') { const rem = e && typeof e.rem_losses === 'number' ? e.rem_losses : null; return nm(it.team) + (rem === 0 ? ' wins out' : rem === null ? ' ends with ' + it.losses + (it.losses === 1 ? ' loss' : ' losses') : ' loses ' + rem + ' of the remaining games'); }
    return nm(it.team) + ' wins ' + it.n + ' of ' + (it.scope === 'remaining' ? 'the remaining games' : 'the ' + it.scope + ' ' + it.m);
  };
};
