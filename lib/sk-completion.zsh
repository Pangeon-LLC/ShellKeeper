#compdef sk
# Zsh completion for ShellKeeper (sk)
# Copy to a directory in your $fpath (e.g., ~/.zsh/completions/_sk)
# or source this file directly

_sk_sessions() {
    local sessions_dir="$HOME/.shellkeeper/sessions"
    if [[ -d "$sessions_dir" ]]; then
        local sessions=("${(@f)$(ls -1 "$sessions_dir" 2>/dev/null | sed 's/\.sock$//')}")
        _describe 'session' sessions
    fi
}

_sk_profiles() {
    local profiles=("${(@f)$(gsettings get org.gnome.Terminal.ProfilesList list 2>/dev/null | \
        tr -d "[]'" | tr ',' '\n' | while read uuid; do
            gsettings get "org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:$uuid/" visible-name 2>/dev/null | tr -d "'"
        done)}")
    _describe 'profile' profiles
}

_sk() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \
        '1: :->command' \
        '*:: :->args'

    case $state in
        command)
            local commands=(
                'new:Create new session'
                'attach:Attach to session'
                'a:Attach to session (alias)'
                'ls:List sessions'
                'list:List sessions'
                'kill:Kill session'
                'rename:Rename session'
                'clean:Clean dead sessions'
                'info:Show session details'
                'note:Add note to session'
                'cleanup:Remove idle sessions'
                'terminal:Open new terminal with session'
                'term:Open new terminal (alias)'
                'restore:Restore session in new terminal'
                'restore-all:Restore all sessions'
                'profiles:Manage GNOME Terminal profiles'
                'metadata:Manage session metadata'
                'config:Manage configuration'
                'setup-autostart:Set up login restoration'
                'last:Attach to most recent session'
            )
            _describe 'command' commands
            _sk_sessions
            ;;
        args)
            case $words[1] in
                new)
                    _arguments \
                        '1:session name:' \
                        '--profile[GNOME Terminal profile]:profile:_sk_profiles' \
                        '-p[GNOME Terminal profile]:profile:_sk_profiles' \
                        '--match[Inherit current profile]' \
                        '-m[Inherit current profile]'
                    ;;
                attach|a|info|i|restore)
                    _sk_sessions
                    ;;
                kill)
                    _arguments \
                        '1:session name:_sk_sessions' \
                        '--all[Kill all sessions]' \
                        '-a[Kill all sessions]' \
                        '--pattern[Kill by pattern]:pattern:' \
                        '-p[Kill by pattern]:pattern:'
                    ;;
                rename)
                    _arguments \
                        '1:old name:_sk_sessions' \
                        '2:new name:'
                    ;;
                note)
                    _arguments \
                        '1:session name:_sk_sessions' \
                        '2:note text:'
                    ;;
                cleanup)
                    _arguments \
                        '1:max idle days:'
                    ;;
                terminal|term)
                    _arguments \
                        '--profile[GNOME Terminal profile]:profile:_sk_profiles' \
                        '-p[GNOME Terminal profile]:profile:_sk_profiles' \
                        '--match[Inherit current profile]' \
                        '-m[Inherit current profile]'
                    ;;
                profiles)
                    local subcmds=(
                        'list:List profiles'
                        'default:Show default profile'
                    )
                    _describe 'subcommand' subcmds
                    ;;
                metadata)
                    local subcmds=(
                        'list:List all metadata'
                        'clean:Clean orphaned metadata'
                        'export:Export metadata'
                        'import:Import metadata'
                    )
                    _describe 'subcommand' subcmds
                    ;;
                config)
                    local subcmds=(
                        'show:Show configuration'
                        'set-default-profile:Set default profile'
                    )
                    _describe 'subcommand' subcmds
                    ;;
                set-default-profile)
                    _sk_profiles
                    ;;
            esac
            ;;
    esac
}

_sk "$@"
