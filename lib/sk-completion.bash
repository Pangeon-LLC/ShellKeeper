# Bash completion for ShellKeeper (sk)
# Source this file or copy to /etc/bash_completion.d/sk

_sk_sessions() {
    local sessions_dir="$HOME/.shellkeeper/sessions"
    if [ -d "$sessions_dir" ]; then
        ls -1 "$sessions_dir" 2>/dev/null | sed 's/\.sock$//'
    fi
}

_sk_profiles() {
    gsettings get org.gnome.Terminal.ProfilesList list 2>/dev/null | \
        tr -d "[]'" | tr ',' '\n' | while read uuid; do
            gsettings get "org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:$uuid/" visible-name 2>/dev/null | tr -d "'"
        done
}

_sk_completions() {
    local cur prev words cword
    _init_completion || return

    local commands="new attach ls list kill rename clean info note cleanup terminal restore restore-all profiles metadata config setup-autostart last"

    case "$prev" in
        sk)
            COMPREPLY=($(compgen -W "$commands $(_sk_sessions)" -- "$cur"))
            return
            ;;
        attach|a|kill|info|i|restore|note)
            COMPREPLY=($(compgen -W "$(_sk_sessions)" -- "$cur"))
            return
            ;;
        rename)
            COMPREPLY=($(compgen -W "$(_sk_sessions)" -- "$cur"))
            return
            ;;
        profiles)
            COMPREPLY=($(compgen -W "list default" -- "$cur"))
            return
            ;;
        metadata)
            COMPREPLY=($(compgen -W "list clean export import" -- "$cur"))
            return
            ;;
        config)
            COMPREPLY=($(compgen -W "show set-default-profile" -- "$cur"))
            return
            ;;
        set-default-profile)
            COMPREPLY=($(compgen -W "$(_sk_profiles)" -- "$cur"))
            return
            ;;
        --profile|-p)
            COMPREPLY=($(compgen -W "$(_sk_profiles)" -- "$cur"))
            return
            ;;
        --pattern)
            # Suggest session patterns
            COMPREPLY=($(compgen -W "$(_sk_sessions)" -- "$cur"))
            return
            ;;
    esac

    # Handle options
    case "$cur" in
        -*)
            case "${words[1]}" in
                new)
                    COMPREPLY=($(compgen -W "--profile -p --match -m" -- "$cur"))
                    ;;
                kill)
                    COMPREPLY=($(compgen -W "--all -a --pattern -p" -- "$cur"))
                    ;;
                terminal|term)
                    COMPREPLY=($(compgen -W "--profile -p --match -m" -- "$cur"))
                    ;;
                import)
                    COMPREPLY=($(compgen -W "--force -f" -- "$cur"))
                    ;;
            esac
            return
            ;;
    esac

    # Default to session names
    if [[ ${#words[@]} -gt 2 ]]; then
        COMPREPLY=($(compgen -W "$(_sk_sessions)" -- "$cur"))
    fi
}

complete -F _sk_completions sk
