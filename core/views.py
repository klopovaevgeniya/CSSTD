# Этот файл больше не используется.
# Все представления перемещены в views/admin/, views/employee/, views/manager/ и views/public/


def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        project.delete()
        return redirect('admin_projects')

    return render(request, 'admin/projects/delete.html', {
        'project': project
    })
