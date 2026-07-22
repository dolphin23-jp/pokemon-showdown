# Phase 2 Japanese server translation inventory

Generated from commit: `c7b7fc5ed699c9b1cdf91a310d46757f2cfd8c62`

## Summary

- Japanese dictionary keys: 509
- Empty Japanese values: 18
- Tagged translation keys missing from Japanese: 256
- Direct English output candidates bypassing tr: 539

Priority means: P0 = login/common command or correctness blocker; P1 = common public command; P2 = room/plugin/staff workflow; P3 = uncommon/internal.

## Empty dictionary values

| Priority | Source | Command | Text |
| --- | --- | --- | --- |
| P0 | `translations/japanese/helptickets.ts:80` | `-` | Help Ticket Stats |
| P0 | `translations/japanese/helptickets.ts:92` | `-` | Claimed |
| P0 | `translations/japanese/helptickets.ts:93` | `-` | Unclaimed |
| P0 | `translations/japanese/helptickets.ts:94` | `-` | Claim |
| P0 | `translations/japanese/helptickets.ts:103` | `-` | Banned |
| P0 | `translations/japanese/helptickets.ts:104` | `-` | Ticket Stats |
| P0 | `translations/japanese/helptickets.ts:105` | `-` | No ticket stats found. |
| P0 | `translations/japanese/helptickets.ts:107` | `-` | Staff Stats |
| P0 | `translations/japanese/helptickets.ts:109` | `-` | Resolved |
| P0 | `translations/japanese/helptickets.ts:110` | `-` | Unresolved |
| P0 | `translations/japanese/helptickets.ts:111` | `-` | Dead |
| P0 | `translations/japanese/helptickets.ts:113` | `-` | Total Tickets |
| P0 | `translations/japanese/helptickets.ts:114` | `-` | Average Total Time |
| P0 | `translations/japanese/helptickets.ts:115` | `-` | Average Initial Wait |
| P0 | `translations/japanese/helptickets.ts:116` | `-` | Average Total Wait |
| P0 | `translations/japanese/helptickets.ts:117` | `-` | Resolutions |
| P0 | `translations/japanese/helptickets.ts:118` | `-` | Positive Result |
| P0 | `translations/japanese/helptickets.ts:121` | `-` | Average Time Per Ticket |

## Missing Japanese dictionary keys

| Priority | Source | Command | Text |
| --- | --- | --- | --- |
| P1 | `server/chat-commands/core.ts:188` | `version` | Server version: <b>${version} |
| P1 | `server/chat-commands/core.ts:357` | `msg` | User ${targetUsername} is offline. Send the message again to confirm. If you are using /msg, use /offlinemsg instead. |
| P1 | `server/chat-commands/core.ts:504` | `blockpms` | You are already blocking ${msg}private messages! To unblock, use /unblockpms |
| P1 | `server/chat-commands/core.ts:508` | `blockpms` | You are now blocking ${msg}private messages, except from staff and ${target}. |
| P1 | `server/chat-commands/core.ts:512` | `blockpms` | You are now blocking ${msg}private messages, except from staff, friends, and ${target} users. |
| P1 | `server/chat-commands/core.ts:515` | `blockpms` | You are now blocking ${msg}private messages, except from staff and friends. |
| P1 | `server/chat-commands/core.ts:518` | `blockpms` | You are now blocking ${msg}private messages, except from staff. |
| P1 | `server/chat-commands/core.ts:545` | `unblockpms` | You are not blocking ${msg}private messages! To block, use /blockpms |
| P1 | `server/chat-commands/core.ts:554` | `unblockpms` | You are no longer blocking ${msg}private messages. |
| P1 | `server/chat-commands/core.ts:577` | `blockinvites` | You are now blocking room invites, except from staff and ${target}. |
| P1 | `server/chat-commands/core.ts:580` | `blockinvites` | You are now blocking room invites, except from staff and ${target} users. |
| P1 | `server/chat-commands/core.ts:583` | `blockinvites` | You are now blocking room invites, except from staff. |
| P1 | `server/chat-commands/core.ts:694` | `rank` | Format |
| P1 | `server/chat-commands/core.ts:694` | `rank` | L |
| P1 | `server/chat-commands/core.ts:694` | `rank` | Total |
| P1 | `server/chat-commands/core.ts:694` | `rank` | W |
| P1 | `server/chat-commands/core.ts:863` | `exportinputlog` | ${user.name} wants to extract the battle input log. |
| P1 | `server/chat-commands/core.ts:917` | `showset` | You are not a player and don't have a team. |
| P1 | `server/chat-commands/core.ts:924` | `showset` | You don't have a Pokémon matching "${target}" in your team. |
| P1 | `server/chat-commands/core.ts:930` | `showset` | You don't have a Pokémon #${parsed} on your team - your team only has ${team.length} Pokémon. |
| P1 | `server/chat-commands/core.ts:962` | `acceptopenteamsheets` | Must be a player to agree to open team sheets. |
| P1 | `server/chat-commands/core.ts:966` | `acceptopenteamsheets` | This format does not allow requesting open team sheets. You can both manually agree to it by using !showteam hidestats. |
| P1 | `server/chat-commands/core.ts:969` | `acceptopenteamsheets` | You cannot agree to open team sheets after Team Preview. Each player can still show their own sheet by using this command: !showteam hidestats |
| P1 | `server/chat-commands/core.ts:972` | `acceptopenteamsheets` | An opponent has already rejected open team sheets. |
| P1 | `server/chat-commands/core.ts:975` | `acceptopenteamsheets` | You have already made your decision about agreeing to open team sheets. |
| P1 | `server/chat-commands/core.ts:980` | `acceptopenteamsheets` | ${user.name} has agreed to open team sheets. |
| P1 | `server/chat-commands/core.ts:993` | `rejectopenteamsheets` | Must be a player to reject open team sheets. |
| P1 | `server/chat-commands/core.ts:997` | `rejectopenteamsheets` | This format does not allow requesting open team sheets. |
| P1 | `server/chat-commands/core.ts:1000` | `rejectopenteamsheets` | You cannot reject open team sheets after Team Preview. |
| P1 | `server/chat-commands/core.ts:1009` | `rejectopenteamsheets` | ${user.name} rejected open team sheets. |
| P1 | `server/chat-commands/core.ts:1191` | `invitebattle` | Player must be set to "p1" or "p2", not "${slot}". |
| P1 | `server/chat-commands/core.ts:1207` | `invitebattle` | This room already has a player in slot ${slot}. |
| P1 | `server/chat-commands/core.ts:1215` | `invitebattle` | ${targetUser.name} is already a player in this battle. |
| P1 | `server/chat-commands/core.ts:1221` | `invitebattle` | The user '${targetUser.name}' is not accepting challenges right now. |
| P1 | `server/chat-commands/core.ts:1361` | `kickgame` | ${targetUser.name} was kicked from a battle by ${user.name}.${displayReason} |
| P1 | `server/chat-commands/core.ts:1538` | `blockchallenges` | You are now blocking challenges, except from staff and ${target}. |
| P1 | `server/chat-commands/core.ts:1543` | `blockchallenges` | You are now blocking challenges, except from staff and ${target} users. |
| P1 | `server/chat-commands/core.ts:1803` | `help` | '/${target}' is a help command. |
| P1 | `server/chat-commands/info.ts:2078` | `rules` | ${room.title} room rules |
| P1 | `server/chat-commands/info.ts:2079` | `rules` | /rules |
| P1 | `server/chat-commands/info.ts:2100` | `rules` | ${possibleRoom.title} room rules |
| P1 | `server/chat-commands/info.ts:2164` | `faq` | pages/proxyhelp |
| P1 | `server/chat-commands/info.ts:2164` | `faq` | Proxy lock help |
| P1 | `server/chat-commands/info.ts:2167` | `faq` | Custom avatars are given to Global Staff members, contributors (coders and spriters) to Pokemon Showdown, and Smogon badgeholders at the discretion of the PS! Administrators. They are also sometimes given out as rewards for major events such as PSPL (Pokemon Showdown Premier League). If you're curious, you can view the entire list of <a href="https://www.smogon.com/smeargle/customs/">custom avatars</a>. |
| P1 | `server/chat-commands/info.ts:2170` | `faq` | pages/privacy |
| P1 | `server/chat-commands/info.ts:2170` | `faq` | Pokémon Showdown privacy policy |
| P1 | `server/chat-commands/moderation.ts:1910` | `forceclearstatus` | ${targetUser.name}'s status "${targetUser.userMessage}" was cleared by ${user.name}${displayReason}. |
| P2 | `server/chat-plugins/announcements.ts:125` | `edit` | The announcement was edited by ${user.name}. |
| P2 | `server/chat-plugins/announcements.ts:142` | `timer` | Time should be a number of minutes less than one week. |
| P2 | `server/chat-plugins/friends.ts:160` | `checkCanUse` | To use the friends feature you must be autoconfirmed, which means being registered for at least one week and winning one rated game. |
| P2 | `server/chat-plugins/friends.ts:266` | `add` | That name is too long - choose a valid name. |
| P2 | `server/chat-plugins/friends.ts:297` | `accept` | You are currently blocking friend requests, and so cannot accept your own. |
| P2 | `server/chat-plugins/friends.ts:329` | `toggle` | You already are allowing friend requests. |
| P2 | `server/chat-plugins/friends.ts:331` | `toggle` | You are now allowing friend requests. |
| P2 | `server/chat-plugins/friends.ts:333` | `toggle` | You already are blocking incoming friend requests. |
| P2 | `server/chat-plugins/friends.ts:335` | `toggle` | You are now blocking incoming friend requests. |
| P2 | `server/chat-plugins/friends.ts:337` | `toggle` | Unrecognized setting. |
| P2 | `server/chat-plugins/friends.ts:364` | `viewnotifications` | You are already not receiving friend notifications. |
| P2 | `server/chat-plugins/friends.ts:366` | `viewnotifications` | You will not receive friend notifications. |
| P2 | `server/chat-plugins/friends.ts:382` | `togglelogins` | You are already hiding your logins from friends. |
| P2 | `server/chat-plugins/friends.ts:387` | `togglelogins` | You are already allowing friends to see your login times. |
| P2 | `server/chat-plugins/friends.ts:403` | `listdisplay` | You are already allowing other people to view your friends list. |
| P2 | `server/chat-plugins/friends.ts:407` | `listdisplay` | You are now allowing other people to view your friends list. |
| P2 | `server/chat-plugins/friends.ts:410` | `listdisplay` | You are already hiding your friends list. |
| P2 | `server/chat-plugins/friends.ts:414` | `listdisplay` | You are now hiding your friends list. |
| P2 | `server/chat-plugins/friends.ts:434` | `sharebattles` | You are already sharing your battles with friends. |
| P2 | `server/chat-plugins/friends.ts:440` | `sharebattles` | You are already not sharing your battles with friends. |
| P2 | `server/chat-plugins/helptickets.ts:1512` | `request` | If someone is harassing you in private messages (PMs), click the button below and a global staff member will take a look. If you are being harassed in a chatroom, please ask a room staff member to handle it. |
| P2 | `server/chat-plugins/helptickets.ts:1521` | `request` | If someone is harassing you in a battle, click the button below and a global staff member will take a look. If you are being harassed in a chatroom, please ask a room staff member to handle it. |
| P2 | `server/chat-plugins/helptickets.ts:1660` | `request` | If you must use a proxy / VPN to access Pokemon Showdown (e.g. your school blocks the site normally), you will only be able to battle, not chat. When you go home, you will be unlocked and able to freely chat again. |
| P2 | `server/chat-plugins/helptickets.ts:1662` | `request` | If you are certain that you are not currently using a proxy / VPN, please continue and open a ticket. Please explain in detail how you are connecting to Pokemon Showdown. |
| P2 | `server/chat-plugins/helptickets.ts:1672` | `request` | If the semilock does not go away, you can try asking a global staff member for help. |
| P2 | `server/chat-plugins/helptickets.ts:1675` | `request` | If you don't have an autoconfirmed account, you will need to contact a global staff member to appeal your semilock. |
| P2 | `server/chat-plugins/helptickets.ts:1814` | `tickets` | And ${sortedTickets.length - count} more tickets. |
| P2 | `server/chat-plugins/helptickets.ts:1862` | `tickets` | Ticket Bans |
| P2 | `server/chat-plugins/helptickets.ts:1881` | `text` | Queued Tickets |
| P2 | `server/chat-plugins/helptickets.ts:2257` | `create` | You need to choose a username before doing this. |
| P2 | `server/chat-plugins/helptickets.ts:2722` | `close` | ${targetUsername} does not have an open ticket. |
| P2 | `server/chat-plugins/helptickets.ts:2852` | `unban` | ${target} is not ticket banned. |
| P2 | `server/chat-plugins/poll.ts:81` | `select` | That option is already selected. |
| P2 | `server/chat-plugins/poll.ts:415` | `new` | Extra escape character. To end a poll with '\', enter it as '\\' |
| P2 | `server/chat-plugins/poll.ts:449` | `new` | Too many options for poll (maximum is ${MAX_QUESTIONS}). |
| P2 | `server/chat-plugins/poll.ts:496` | `deletequeue` | Can't delete poll at slot ${target} - "${target}" is not a number. |
| P2 | `server/chat-plugins/poll.ts:575` | `timer` | The poll timer was turned on: the poll will end in ${Chat.toDurationString(timeoutMins * MINUTES)}. |
| P2 | `server/chat-plugins/poll.ts:577` | `timer` | The poll timer was set to ${timeoutMins} minute(s) by ${user.name}. |
| P2 | `server/chat-plugins/poll.ts:581` | `timer` | The poll timer is on and will end in ${Chat.toDurationString(poll.timeoutMins * MINUTES)}. |
| P2 | `server/chat-plugins/repeats.ts:143` | `repeats` | every ${minutes} chat message(s) |
| P2 | `server/chat-plugins/trivia/trivia.ts:153` | `-` | There is no game in progress. |
| P2 | `server/chat-plugins/trivia/trivia.ts:156` | `-` | The currently running game is not Trivia, it's ${game.title}. |
| P2 | `server/chat-plugins/trivia/trivia.ts:170` | `-` | The currently running game is not Mastermind, it's ${game.title}. |
| P2 | `server/chat-plugins/trivia/trivia.ts:401` | `-` | Random (${category}) |
| P2 | `server/chat-plugins/trivia/trivia.ts:454` | `addTriviaPlayer` | You have already signed up for this game. |
| P2 | `server/chat-plugins/trivia/trivia.ts:460` | `addTriviaPlayer` | You were kicked from the game and thus cannot join it again. |
| P2 | `server/chat-plugins/trivia/trivia.ts:467` | `addTriviaPlayer` | You were kicked from the game and cannot join until the next game. |
| P2 | `server/chat-plugins/trivia/trivia.ts:483` | `addTriviaPlayer` | This game does not allow latejoins. |
| P2 | `server/chat-plugins/trivia/trivia.ts:524` | `init` | Mode: ${this.game.mode} \| Category: ${this.game.category} \| Cap: ${this.getDisplayableCap()}<br /> |
| P2 | `server/chat-plugins/trivia/trivia.ts:525` | `init` | Sign up for the Trivia game! |
| P2 | `server/chat-plugins/trivia/trivia.ts:526` | `init` |  (You can also type <code>/trivia join</code> to sign up manually.) |
| P2 | `server/chat-plugins/trivia/trivia.ts:531` | `getDescription` | Mode: ${this.game.mode} \| Category: ${this.game.category} \| Cap: ${this.getDisplayableCap()} |
| P2 | `server/chat-plugins/trivia/trivia.ts:551` | `kick` | User ${user.name} has already been kicked from the game. |

## Direct English output candidates

| Priority | Source | Command | Text |
| --- | --- | --- | --- |
| P1 | `server/chat-commands/admin.ts:70` | `-` | Fetching newest version of code in the repository ${codePath}... |
| P1 | `server/chat-commands/admin.ts:75` | `-` | There were no updates. |
| P1 | `server/chat-commands/admin.ts:92` | `-` | Saving changes... |
| P1 | `server/chat-commands/admin.ts:97` | `-` | Rebasing... |
| P1 | `server/chat-commands/admin.ts:106` | `-` | Restoring saved changes... |
| P1 | `server/chat-commands/admin.ts:296` | `setnamecolor` | ${userid}'s namecolor was removed. |
| P1 | `server/chat-commands/admin.ts:435` | `sendhtmlpage` | Closed the bot page ${pageid} for ${Chat.toListString(successes)}. |
| P1 | `server/chat-commands/admin.ts:438` | `sendhtmlpage` | Unable to close the bot page for ${Chat.toListString(errors)}. |
| P1 | `server/chat-commands/admin.ts:442` | `sendhtmlpage` | Sent ${Chat.toListString(successes)}${selector ? ` the selector ${selector} on` : ''} the bot page ${pageid}. |
| P1 | `server/chat-commands/admin.ts:445` | `sendhtmlpage` | Unable to send the bot page ${pageid} to ${Chat.toListString(errors)}. |
| P1 | `server/chat-commands/admin.ts:488` | `highlighthtmlpage` | Sent a highlight to ${targetUser.name} on the bot page ${pageid}. |
| P1 | `server/chat-commands/admin.ts:542` | `sendprivatehtmlbox` | Sent private HTML to ${Chat.toListString(successes)}. |
| P1 | `server/chat-commands/admin.ts:543` | `sendprivatehtmlbox` | Unable to send private HTML to ${Chat.toListString(errors)}. |
| P1 | `server/chat-commands/admin.ts:563` | `botmsg` | The user "${targetUser.name}" is not a bot in this room. |
| P1 | `server/chat-commands/admin.ts:650` | `hotpatch` | Hotpatching chat commands... |
| P1 | `server/chat-commands/admin.ts:668` | `hotpatch` | Reloading chat plugins... |
| P1 | `server/chat-commands/admin.ts:670` | `hotpatch` | DONE |
| P1 | `server/chat-commands/admin.ts:678` | `hotpatch` | Hotpatching processmanager prototypes... |
| P1 | `server/chat-commands/admin.ts:715` | `hotpatch` | DONE |
| P1 | `server/chat-commands/admin.ts:734` | `hotpatch` | Hotpatching ${message}... |
| P1 | `server/chat-commands/admin.ts:762` | `hotpatch` | DONE |
| P1 | `server/chat-commands/admin.ts:772` | `hotpatch` | Hotpatching tournaments... |
| P1 | `server/chat-commands/admin.ts:776` | `hotpatch` | DONE |
| P1 | `server/chat-commands/admin.ts:787` | `hotpatch` | Hotpatching formats... |
| P1 | `server/chat-commands/admin.ts:804` | `hotpatch` | DONE |
| P1 | `server/chat-commands/admin.ts:806` | `hotpatch` | Hotpatching loginserver... |
| P1 | `server/chat-commands/admin.ts:809` | `hotpatch` | DONE. New login server requests will use the new code. |
| P1 | `server/chat-commands/admin.ts:818` | `hotpatch` | Hotpatching validator... |
| P1 | `server/chat-commands/admin.ts:823` | `hotpatch` | DONE. Any battles started after now will have teams be validated according to the new code. |
| P1 | `server/chat-commands/admin.ts:829` | `hotpatch` | Hotpatching punishments... |
| P1 | `server/chat-commands/admin.ts:831` | `hotpatch` | DONE |
| P1 | `server/chat-commands/admin.ts:833` | `hotpatch` | Hotpatching ip-tools... |
| P1 | `server/chat-commands/admin.ts:837` | `hotpatch` | DONE |
| P1 | `server/chat-commands/admin.ts:851` | `hotpatch` | Hotpatching modlog... |
| P1 | `server/chat-commands/admin.ts:856` | `hotpatch` | DONE |
| P1 | `server/chat-commands/admin.ts:858` | `hotpatch` | Disabling hot-patch has been moved to its own command: |
| P1 | `server/chat-commands/admin.ts:919` | `nohotpatch` | You have enabled hot-patching ${hotpatch}. |
| P1 | `server/chat-commands/admin.ts:928` | `nohotpatch` | You have disabled hot-patching ${hotpatch}. |
| P1 | `server/chat-commands/admin.ts:1038` | `savelearnsets` | saving... |
| P1 | `server/chat-commands/admin.ts:1051` | `savelearnsets` | learnsets.js saved. |
| P1 | `server/chat-commands/admin.ts:1089` | `adddatacenters` | This command has been replaced by /datacenter add |
| P1 | `server/chat-commands/admin.ts:1148` | `lockdown` | ${Chat.count(disabledCommands.length, "commands")} are disabled right now. |
| P1 | `server/chat-commands/admin.ts:1149` | `lockdown` | Be aware that restarting will re-enable them. |
| P1 | `server/chat-commands/admin.ts:1150` | `lockdown` | Currently disabled: ${disabledCommands.join(', ')} |
| P1 | `server/chat-commands/admin.ts:1227` | `endlockdown` | Preparation for the server shutdown was canceled. |
| P1 | `server/chat-commands/admin.ts:1296` | `savebattles` | Saving battles... |
| P1 | `server/chat-commands/admin.ts:1298` | `savebattles` | DONE. |
| P1 | `server/chat-commands/admin.ts:1299` | `savebattles` | ${count} battles saved. |
| P1 | `server/chat-commands/admin.ts:1317` | `kill` | Saving battles... |
| P1 | `server/chat-commands/admin.ts:1327` | `kill` | DONE. |
| P1 | `server/chat-commands/admin.ts:1328` | `kill` | ${count} battles saved. |
| P1 | `server/chat-commands/admin.ts:1415` | `updateloginserver` | Restarting... |
| P1 | `server/chat-commands/admin.ts:1431` | `updateloginserver` | DONE. Server updated and restarted. |
| P1 | `server/chat-commands/admin.ts:1434` | `updateloginserver` | FAILED. Conflicts were found while updating - the restart was aborted. |
| P1 | `server/chat-commands/admin.ts:1446` | `updateclient` | Restarting... |
| P1 | `server/chat-commands/admin.ts:1464` | `updateclient` | DONE. Client updated. |
| P1 | `server/chat-commands/admin.ts:1467` | `updateclient` | FAILED. Conflicts were found while updating. |
| P1 | `server/chat-commands/admin.ts:1484` | `rebuild` | Rebuilt. |
| P1 | `server/chat-commands/admin.ts:1494` | `bash` | $ ${target} |
| P1 | `server/chat-commands/admin.ts:1497` | `bash` | ${stdout}${stderr} |
| P1 | `server/chat-commands/admin.ts:1539` | `eval` | ${command}${generateHTML('<', message)} |
| P1 | `server/chat-commands/core.ts:293` | `linksmogon` | Linking... |
| P1 | `server/chat-commands/core.ts:412` | `offlinemsg` | That user is online, so a normal PM is being sent. |
| P1 | `server/chat-commands/core.ts:569` | `blockinvites` | You are no longer blocking room invites. |
| P1 | `server/chat-commands/core.ts:1576` | `cancelchallenge` | You are not challenging ${this.pmTarget.name}. Maybe they accepted/rejected before you cancelled? |
| P1 | `server/chat-commands/core.ts:1595` | `accept` | ${this.pmTarget.id} is not challenging you. Maybe they cancelled before you accepted? |
| P1 | `server/chat-commands/core.ts:1617` | `reject` | ${this.pmTarget.id} is not challenging you. Maybe they cancelled before you rejected? |
| P1 | `server/chat-commands/core.ts:1646` | `vtm` | ${(matchMessage ? matchMessage + "\n\n" : "")}${this.tr`Your team is valid for ${format.name}.`} |
| P1 | `server/chat-commands/core.ts:1648` | `vtm` | ${(matchMessage ? matchMessage + "\n\n" : "")}${this.tr`Your team was rejected for the following reasons:`}  - ${result.slice(1).replace(/\n/g, '\n- ')} |
| P1 | `server/chat-commands/core.ts:1721` | `help` | ${this.tr`COMMANDS`}: /report, /msg, /reply, /logout, /challenge, /search, /rating, /whois, /user, /join, /leave, /userauth, /roomauth |
| P1 | `server/chat-commands/core.ts:1722` | `help` | ${this.tr`BATTLE ROOM COMMANDS`}: /savereplay, /hideroom, /inviteonly, /invite, /timer, /forfeit |
| P1 | `server/chat-commands/core.ts:1723` | `help` | ${this.tr`OPTION COMMANDS`}: /nick, /avatar, /ignore, /status, /away, /busy, /back, /timestamps, /highlight, /showjoins, /hidejoins, /blockchallenges, /blockpms |
| P1 | `server/chat-commands/core.ts:1724` | `help` | ${this.tr`INFORMATIONAL/RESOURCE COMMANDS`}: /groups, /faq, /rules, /intro, /formatshelp, /othermetas, /analysis, /punishments, /calc, /git, /cap, /roomhelp, /roomfaq ${broadcastMsg} |
| P1 | `server/chat-commands/core.ts:1725` | `help` | ${this.tr`DATA COMMANDS`}: /data, /dexsearch, /movesearch, /itemsearch, /learn, /statcalc, /effectiveness, /weakness, /coverage, /randommove, /randompokemon ${broadcastMsg} |
| P1 | `server/chat-commands/core.ts:1727` | `help` | ${this.tr`DRIVER COMMANDS`}: /warn, /mute, /hourmute, /unmute, /alts, /forcerename, /modlog, /modnote, /modchat, /lock, /weeklock, /unlock, /announce |
| P1 | `server/chat-commands/core.ts:1728` | `help` | ${this.tr`MODERATOR COMMANDS`}: /globalban, /unglobalban, /ip, /markshared, /unlockip |
| P1 | `server/chat-commands/core.ts:1729` | `help` | ${this.tr`ADMIN COMMANDS`}: /declare, /forcetie, /forcewin, /promote, /demote, /banip, /host, /ipsearch |
| P1 | `server/chat-commands/info.ts:443` | `sharedbattles` | ${targetUsername1} and ${targetUsername2} have no common battles. |
| P1 | `server/chat-commands/info.ts:476` | `host` | IP ${target}: ${host \|\| "ERROR"} [${hostType}]${dnsblMessage} |
| P1 | `server/chat-commands/info.ts:497` | `ipsearch` | Users with host ${ipOrHost}${targetRoom ? ` in the room ${targetRoom.title}` : ``}: |
| P1 | `server/chat-commands/info.ts:506` | `ipsearch` | Users with IP ${ipOrHost}${targetRoom ? ` in the room ${targetRoom.title}` : ``}: |
| P1 | `server/chat-commands/info.ts:514` | `ipsearch` | Users in IP range ${ipOrHost}${targetRoom ? ` in the room ${targetRoom.title}` : ``}: |
| P1 | `server/chat-commands/info.ts:527` | `ipsearch` | No users found. |
| P1 | `server/chat-commands/info.ts:531` | `ipsearch` | More than 100 users found. Use /ipsearchall for the full list. |
| P1 | `server/chat-commands/info.ts:541` | `checkchallenges` | This command must be broadcast: |
| P1 | `server/chat-commands/info.ts:568` | `ignore` | In PMs, this command can only be used by itself to ignore the person you're talking to: "/${this.cmd}", not "/${this.cmd} ${target}" |
| P1 | `server/chat-commands/info.ts:570` | `ignore` | You're using a custom client that doesn't support the ignore command. |
| P1 | `server/chat-commands/info.ts:1002` | `weakness` | No Pokémon or type named '${originalSearch}' was found${Dex.gen > dex.gen ? ` in Gen ${dex.gen}` : ""}. Searching for '${target}' instead. |
| P1 | `server/chat-commands/info.ts:1136` | `effectiveness` | ${atkName} is ${factor}x effective against ${defName}.${additionalInfo} |
| P1 | `server/chat-commands/info.ts:1167` | `coverage` | The full table cannot be broadcast. |
| P1 | `server/chat-commands/info.ts:1317` | `coverage` | Coverage for ${sources.join(' + ')}:<br />${buffer} |
| P1 | `server/chat-commands/info.ts:1372` | `statcalc` | Level should be between 1 and 9999. |
| P1 | `server/chat-commands/info.ts:1462` | `statcalc` | The amount of EVs should be between 0 and 255. |
| P1 | `server/chat-commands/info.ts:1495` | `statcalc` | Modifier should be a number between -6 and +6 |
| P1 | `server/chat-commands/info.ts:1511` | `statcalc` | The target real stat must be greater than 0. |
| P1 | `server/chat-commands/info.ts:1527` | `statcalc` | No stat found. |
| P1 | `server/chat-commands/info.ts:1548` | `statcalc` | No valid value for base stat possible with given parameters. |
| P1 | `server/chat-commands/info.ts:1566` | `statcalc` | No valid EV/IV combination possible with given parameters. Maybe try a different nature?${ev} |
| P1 | `server/chat-commands/info.ts:1569` | `statcalc` | Too many parameters given; nothing to calculate. |
| P1 | `server/chat-commands/info.ts:1572` | `statcalc` | No valid value for base stat found. |

The JSON report contains the complete, untruncated inventories.
