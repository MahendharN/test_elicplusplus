name: Generate Release Notes

on:
  pull_request:
    types: [closed]

jobs:
  generate_release_notes:
    runs-on: ubuntu-latest
    
    if: |
      github.event.pull_request.merged == true &&
      contains(github.event.pull_request.title, 'Pr for Release Notes of') &&
      (
        startsWith(github.event.pull_request.base.ref, 'rc_') ||
        endsWith(github.event.pull_request.base.ref, '.x') ||
        github.event.pull_request.base.ref == 'develop'
      )

    steps:
    - name: Checkout code
      uses: actions/checkout@v2
      
    - name: Generate release notes
      id: release_notes
      run: |
        if [[ -z "${{ github.event.pull_request.body }}" ]]; then
          echo "PR description is empty."
          exit 1
        fi
        
        tag_name=$(echo "${{ github.event.pull_request.body }}" | grep -oE "Tag: (.*)" | cut -d' ' -f2)
        if [[ -z "$tag_name" ]]; then
          echo "Tag not found in PR description."
          exit 1
        fi
        
        echo "::set-output name=tag_name::$tag_name"
        
    - name: Create Release
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: ${{ steps.release_notes.outputs.tag_name }}
        release_name: Release ${{ steps.release_notes.outputs.tag_name }}
        body: |
          Release notes for tag ${{ steps.release_notes.outputs.tag_name }}.
          Add your release notes here.
