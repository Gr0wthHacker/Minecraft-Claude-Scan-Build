## The daily loop

```bash
python -m mcbuild sync            # cut the newest scan, regenerate ground designs, progress + shop, learn, BACK UP
python -m mcbuild backup --status # what backups exist and how old the newest is
python -m mcbuild craft <design>  # what it is MADE of, against your containers
```
`sync.yaml` says which designs regenerate and which get reported. After that:

```bash
python -m mcbuild progress <design...> --world out/island_now.litematic
python -m mcbuild shop <design...> --world out/island_now.litematic --have
python -m mcbuild card <design> --world out/island_now.litematic     # one PNG for chat
python -m mcbuild diff <old scan> <new scan>
```
In game: `/cscan island` to scan, `/cscan place` to place every design at its recorded origin.
While building:
```
/cscan need <design>     materials for the unbuilt cells within 48 blocks + which chest holds each
/cscan next <design>     the next 24 cells, marked green, lowest first so you never build past reach
/cscan check <design>    cells where the world holds something else, marked amber
```
These read `<design>.work.json`, so run `python -m mcbuild work <design> --ship` if you hand-edit a
design without regenerating it.

